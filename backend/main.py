import os
import json
import asyncio
import logging
import ipaddress
import uuid
import httpx
from urllib.parse import urlparse
from typing import Dict, Any, Optional, Literal, Tuple
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query, File, UploadFile, Request
from fastapi.responses import Response, StreamingResponse
from starlette.background import BackgroundTask
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from config import settings
from database import init_db, get_db, SessionLocal, Product, TriggerRule, LiveLog, RuntimeSetting, SceneSetting
from services.tiktok_connector import TikTokConnector
from services.trigger_engine import TriggerEngine
from services.product_matcher import ProductMatcher
from services.ai_service import AIService
from services.tts_service import TTSService
from services.shop_automation import ShopAutomation
from services.stream_service import MAX_MANIFEST_BYTES, StreamService, StreamSourceError
from services.websocket_manager import (
    ConnectionManager,
    normalize_origins,
    websocket_origin_allowed as _websocket_origin_allowed,
)
from services.interaction_queue import (
    InteractionJobNotFound,
    InteractionQueueError,
    InteractionQueueService,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("livestream_backend")

# Initialize DB tables
init_db()

app = FastAPI(title=settings.APP_NAME)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure static directories exist
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
AUDIO_DIR = os.path.join(STATIC_DIR, "audio")
SCENE_DIR = os.path.join(STATIC_DIR, "scene")
AVATAR_DIR = os.path.join(STATIC_DIR, "avatars")
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(SCENE_DIR, exist_ok=True)
os.makedirs(AVATAR_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        try:
            response = await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404 or "." in os.path.basename(path):
                raise
            response = await super().get_response("index.html", scope)
        if response.status_code == 404 and "." not in os.path.basename(path):
            return await super().get_response("index.html", scope)
        return response


live_ws_manager = ConnectionManager()
scene_ws_manager = ConnectionManager()
ALLOWED_BROWSER_ORIGINS = normalize_origins(settings.CORS_ORIGINS)


def websocket_origin_allowed(websocket: WebSocket) -> bool:
    """Compatibility wrapper around the WebSocket infrastructure policy."""
    return _websocket_origin_allowed(websocket, ALLOWED_BROWSER_ORIGINS)


# Global Services
trigger_engine = TriggerEngine(
    dedup_window_seconds=45,
    global_cooldown_seconds=2.0,
    user_cooldown_seconds=30.0
)
ai_service = AIService(
    provider=settings.DEFAULT_LLM_PROVIDER,
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_BASE_URL,
    model=settings.OPENAI_MODEL
)
tts_service = TTSService(
    voice=settings.EDGE_TTS_VOICE,
    rate=settings.EDGE_TTS_RATE,
    pitch=settings.EDGE_TTS_PITCH
)
shop_automation = ShopAutomation()
stream_service = StreamService()
interaction_queue = InteractionQueueService(
    session_factory=SessionLocal,
    tts_service=tts_service,
    max_queue_size=100,
    tts_timeout_seconds=120.0,
    playback_timeout_seconds=120.0,
)
AI_TIMEOUT_SECONDS = 60.0


def load_runtime_settings() -> None:
    db = SessionLocal()
    try:
        values = {item.key: item.value for item in db.query(RuntimeSetting).all()}
    finally:
        db.close()
    ai_service.provider = values.get("ai.provider", ai_service.provider)
    ai_service.api_key = values.get("ai.api_key", ai_service.api_key)
    ai_service.base_url = values.get("ai.base_url", ai_service.base_url)
    ai_service.model = values.get("ai.model", ai_service.model)
    if values.get("ai.system_prompt", "").strip():
        ai_service.set_system_prompt(values["ai.system_prompt"])
    tts_service.voice = values.get("tts.voice", tts_service.voice)
    tts_service.rate = values.get("tts.rate", tts_service.rate)
    tts_service.pitch = values.get("tts.pitch", tts_service.pitch)


def save_runtime_settings(values: Dict[str, str]) -> None:
    db = SessionLocal()
    try:
        for key, value in values.items():
            item = db.query(RuntimeSetting).filter(RuntimeSetting.key == key).first()
            if item:
                item.value = value
            else:
                db.add(RuntimeSetting(key=key, value=value))
        db.commit()
    finally:
        db.close()


def cleanup_unreferenced_media() -> None:
    db = SessionLocal()
    try:
        setting = db.query(SceneSetting).first()
        referenced = {
            os.path.basename(url)
            for url in (
                setting.avatar_media_url if setting else "",
                setting.video_media_url if setting else "",
            )
            if url and url.startswith("/static/avatars/")
        }
    finally:
        db.close()
    avatar_root = os.path.abspath(AVATAR_DIR)
    for name in os.listdir(avatar_root):
        path = os.path.abspath(os.path.join(avatar_root, name))
        if name not in referenced and os.path.commonpath([path, avatar_root]) == avatar_root and os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                logger.warning("Unable to remove unreferenced media file %s", path)


load_runtime_settings()


# Callback for TikTok Events
async def handle_tiktok_event(event: Dict[str, Any]):
    logger.info(f"Incoming TikTok Event: {event}")
    event_type = event.get("type", "chat")
    user_name = event.get("user_name", "Khán giả")
    user_id = event.get("user_id", user_name)

    # Broadcast raw event to Live Console UI
    await live_ws_manager.broadcast({"type": "raw_event", "data": event})

    if event_type in {"disconnect", "live_end"}:
        await live_ws_manager.broadcast({
            "type": "tiktok_lifecycle",
            "data": {"state": event_type, "username": tiktok_connector.username if "tiktok_connector" in globals() else ""},
        })
        return None

    if event_type == "chat":
        user_message = event.get("comment", "")
    elif event_type == "gift":
        gift_name = event.get("gift_name", "quà tặng")
        repeat_count = event.get("repeat_count", 1)
        user_message = f"Tặng {gift_name} x{repeat_count}"
    elif event_type in {"member", "join"}:
        user_message = "Vừa vào phòng livestream"
    else:
        user_message = f"Sự kiện: {event_type}"

    job = await interaction_queue.create_job(
        event_type=event_type,
        user_id=str(user_id),
        user_name=user_name,
        user_message=user_message,
    )
    if job["status"] == "skipped":
        return job

    if event_type == "chat":
        comment = user_message
        # Evaluate comment through 9-step filter pipeline & cooldowns
        should_process, cleaned_comment, reason = trigger_engine.evaluate_comment(user_name, user_id, comment)

        if not should_process:
            logger.info(f"Comment from '{user_name}' filtered out. Reason: {reason}")
            job = await interaction_queue.mark_skipped(job["id"], reason)
            await live_ws_manager.broadcast({
                "type": "event_filtered",
                "job_id": job["id"],
                "user_name": user_name,
                "comment": comment,
                "reason": reason
            })
            return job

        # Match Product using deterministic 1000-point algorithm
        await interaction_queue.mark_ai_processing(job["id"])
        db = SessionLocal()
        try:
            matcher = ProductMatcher(db, score_threshold=160)
            product, score = matcher.match_comment(cleaned_comment)
            product_ctx = None
            if product:
                product_ctx = f"Sản phẩm: {product.name}, Giá: {product.price}. Điểm nổi bật: {product.selling_points}."
                if product.custom_script:
                    product_ctx += f" Kịch bản tư vấn ưu tiên: {product.custom_script}."

            # Generate AI Reply
            ai_reply = await asyncio.wait_for(
                ai_service.generate_response(user_name, cleaned_comment, product_ctx, event_type="chat"),
                timeout=AI_TIMEOUT_SECONDS,
            )

            # Log to DB
            log_entry = LiveLog(
                event_type="chat",
                user_name=user_name,
                user_message=comment,
                ai_reply=ai_reply,
                status="processed"
            )
            db.add(log_entry)
            db.commit()

            # Broadcast AI response to Live Console UI
            event_response = {
                "type": "ai_response",
                "job_id": job["id"],
                "user_name": user_name,
                "user_message": comment,
                "ai_reply": ai_reply,
                "matched_product": product.name if product else None,
                "match_score": score
            }
            await live_ws_manager.broadcast(event_response)

            # Enqueue for TTS; the next job starts only after real playback ACK.
            job = await interaction_queue.set_ai_reply_and_enqueue(job["id"], ai_reply)

        except Exception as exc:
            reason = "ai_timeout" if isinstance(exc, asyncio.TimeoutError) else str(exc)
            return await interaction_queue.mark_error(job["id"], reason)
        finally:
            db.close()
        return job

    elif event_type in ["gift", "like", "follow", "share", "member", "join"]:
        rule = trigger_engine.event_rules.get(event_type)
        if rule and not rule.get("enabled", True):
            return await interaction_queue.mark_skipped(job["id"], "event_disabled")

        try:
            # Handle non-chat events with templates.
            await interaction_queue.mark_ai_processing(job["id"])
            ai_reply = await asyncio.wait_for(
                ai_service.generate_response(user_name, "", event_type=event_type),
                timeout=AI_TIMEOUT_SECONDS,
            )

            db = SessionLocal()
            try:
                log_entry = LiveLog(
                    event_type=event_type,
                    user_name=user_name,
                    user_message=user_message,
                    ai_reply=ai_reply,
                    status="processed"
                )
                db.add(log_entry)
                db.commit()
            finally:
                db.close()

            await live_ws_manager.broadcast({
                "type": "ai_response",
                "job_id": job["id"],
                "user_name": user_name,
                "user_message": user_message,
                "ai_reply": ai_reply
            })
            return await interaction_queue.set_ai_reply_and_enqueue(job["id"], ai_reply)
        except Exception as exc:
            reason = "ai_timeout" if isinstance(exc, asyncio.TimeoutError) else str(exc)
            return await interaction_queue.mark_error(job["id"], reason)

    return await interaction_queue.mark_skipped(job["id"], "unsupported_event_type")


# Initialize TikTok Connector
tiktok_connector = TikTokConnector(event_callback=handle_tiktok_event)


# Playback commands are leased to exactly one renderer connection.
async def broadcast_tts_to_scene(tts_data: Dict[str, Any]):
    owner = tts_data.get("playback_owner", "")
    renderer_id = tts_data.get("playback_renderer_id", "")
    manager = scene_ws_manager if owner == "scene" else live_ws_manager if owner == "live" else None
    if not manager or not renderer_id or not await manager.send_to(renderer_id, tts_data):
        raise InteractionQueueError("playback_renderer_unavailable")


async def broadcast_interaction_state(message: Dict[str, Any]):
    await live_ws_manager.broadcast(message)


def select_playback_owner() -> Tuple[str, str]:
    scene_id = scene_ws_manager.first_connection_id
    if scene_id:
        return "scene", scene_id
    live_id = live_ws_manager.first_connection_id
    if live_id:
        return "live", live_id
    return "", ""


@app.on_event("startup")
async def startup_event():
    tts_service.cleanup_temp_files()
    cleanup_unreferenced_media()
    await interaction_queue.start(
        broadcast_callback=broadcast_tts_to_scene,
        state_callback=broadcast_interaction_state,
        owner_selector=select_playback_owner,
    )
    logger.info("Application startup complete.")


@app.on_event("shutdown")
async def shutdown_event():
    await interaction_queue.stop()
    await tiktok_connector.disconnect()
    await shop_automation.close()
    await tts_service.shutdown()


# Pydantic Schemas
class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    keywords: str = Field(default="", max_length=2000)
    price: str = Field(default="", max_length=100)
    selling_points: str = Field(default="", max_length=5000)
    custom_script: str = Field(default="", max_length=5000)
    product_link: str = Field(default="", max_length=500)


class TriggerRuleCreate(BaseModel):
    name: str
    event_type: str = "chat"
    keywords: str = ""
    blacklist: str = ""
    action_type: str = "ai_reply"
    reply_template: str = ""
    cooldown_seconds: int = 5
    enabled: bool = True


class TikTokConnectRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)


class AISettingsUpdate(BaseModel):
    provider: Literal["openai", "openrouter", "ollama"]
    api_key: str = Field(default="", max_length=512)
    base_url: str = Field(min_length=8, max_length=500)
    model: str = Field(min_length=1, max_length=200)
    system_prompt: str = Field(default="", max_length=10000)
    clear_api_key: bool = False


class TTSSettingsUpdate(BaseModel):
    voice: str = Field(min_length=1, max_length=100)
    rate: str = Field(pattern=r"^[+-]\d{1,3}%$")
    pitch: str = Field(pattern=r"^[+-]\d{1,4}Hz$")


class TestTTSRequest(BaseModel):
    text: Optional[str] = Field(
        default="Xin chào, hệ thống giọng đọc AI livestream đã sẵn sàng!",
        max_length=1000,
    )


class ManualChatRequest(BaseModel):
    user_name: str = Field(min_length=1, max_length=255)
    comment: str = Field(min_length=1, max_length=2000)


class ManualEventRequest(BaseModel):
    user_name: str = Field(min_length=1, max_length=255)
    event_type: Literal["gift", "follow", "share", "member", "join"] = "member"


class StreamSourceUpdate(BaseModel):
    url: str = Field(min_length=8, max_length=4000)
    label: str = Field(default="", max_length=120)


class InteractionJobCreate(BaseModel):
    event_type: Literal["chat", "gift", "like", "follow", "share", "member", "join"]
    user_name: str = Field(min_length=1, max_length=255)
    user_id: str = Field(default="", max_length=255)
    message: str = Field(default="", max_length=2000)
    gift_name: str = Field(default="", max_length=255)
    repeat_count: int = Field(default=1, ge=1, le=1000000)


class PlaybackAckRequest(BaseModel):
    playback_id: str = Field(min_length=36, max_length=36)
    state: Literal["started", "ended", "failed"]
    source: Literal["scene", "live"]
    error: str = Field(default="", max_length=1000)
    renderer_id: str = Field(default="", max_length=64)


class QueueClearRequest(BaseModel):
    include_current: bool = False


# API Routes
@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": settings.APP_NAME}


@app.post("/api/tiktok/connect")
async def connect_tiktok(req: TikTokConnectRequest):
    success = await tiktok_connector.connect(req.username)
    return {"status": "connected" if success else "failed", "username": req.username}


@app.post("/api/tiktok/disconnect")
async def disconnect_tiktok():
    await tiktok_connector.disconnect()
    return {"status": "disconnected"}


@app.get("/api/tiktok/status")
def get_tiktok_status():
    return {
        "is_connected": tiktok_connector.is_connected,
        "username": tiktok_connector.username
    }


@app.post("/api/manual_chat")
async def send_manual_chat(req: ManualChatRequest):
    job = await handle_tiktok_event({
        "type": "chat",
        "user_name": req.user_name,
        "comment": req.comment,
        "user_id": f"user_{hash(req.user_name) % 10000}"
    })
    return {"status": "accepted", "job": job}


@app.post("/api/manual_event")
async def send_manual_event(req: ManualEventRequest):
    job = await handle_tiktok_event({
        "type": req.event_type,
        "user_name": req.user_name,
        "user_id": f"user_{hash(req.user_name) % 10000}"
    })
    return {"status": "accepted", "job": job}


# Interaction jobs and authoritative playback queue
@app.post("/api/interaction-jobs", status_code=202)
async def create_interaction_job(req: InteractionJobCreate):
    if req.event_type == "chat" and not req.message.strip():
        raise HTTPException(status_code=422, detail="Chat jobs require a message")
    event: Dict[str, Any] = {
        "type": req.event_type,
        "user_name": req.user_name,
        "user_id": req.user_id or f"api_{uuid.uuid4().hex[:12]}",
    }
    if req.event_type == "chat":
        event["comment"] = req.message
    elif req.event_type == "gift":
        event["gift_name"] = req.gift_name or "quà tặng"
        event["repeat_count"] = req.repeat_count
    job = await handle_tiktok_event(event)
    if job and job["status"] == "skipped" and job["decision_reason"] == "queue_full":
        raise HTTPException(status_code=429, detail={"message": "Interaction queue is full", "job": job})
    return {"status": "accepted", "job": job}


@app.get("/api/interaction-jobs")
def list_interaction_jobs(
    limit: int = Query(default=50, ge=1, le=500),
    status: str = Query(default="", max_length=50),
):
    return {"jobs": interaction_queue.list_jobs(limit=limit, status=status)}


@app.get("/api/interaction-jobs/{job_id}")
def get_interaction_job(job_id: str):
    try:
        return interaction_queue.get_job(job_id)
    except InteractionJobNotFound as exc:
        raise HTTPException(status_code=404, detail="Interaction job not found") from exc


@app.post("/api/interaction-jobs/{job_id}/playback")
async def acknowledge_interaction_playback(job_id: str, ack: PlaybackAckRequest):
    try:
        return await interaction_queue.acknowledge_playback(
            job_id=job_id,
            playback_id=ack.playback_id,
            state=ack.state,
            source=ack.source,
            error=ack.error,
            renderer_id=ack.renderer_id,
        )
    except InteractionJobNotFound as exc:
        raise HTTPException(status_code=404, detail="Interaction job not found") from exc
    except InteractionQueueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/interaction-jobs/{job_id}/cancel")
async def cancel_interaction_job(job_id: str):
    try:
        return await interaction_queue.cancel(job_id)
    except InteractionJobNotFound as exc:
        raise HTTPException(status_code=404, detail="Interaction job not found") from exc
    except InteractionQueueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/interaction-jobs/{job_id}/retry")
async def retry_interaction_job(job_id: str):
    try:
        return await interaction_queue.retry(job_id)
    except InteractionJobNotFound as exc:
        raise HTTPException(status_code=404, detail="Interaction job not found") from exc
    except InteractionQueueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/api/interaction-queue")
def get_interaction_queue_status():
    return interaction_queue.status()


@app.post("/api/interaction-queue/skip-current")
async def skip_current_interaction():
    job = await interaction_queue.skip_current()
    return {"job": job, **interaction_queue.status()}


@app.post("/api/interaction-queue/clear")
async def clear_interaction_queue(req: QueueClearRequest = QueueClearRequest()):
    return await interaction_queue.clear(include_current=req.include_current)


# Stream preview
@app.get("/api/stream/status")
def get_stream_status():
    return stream_service.status()


@app.put("/api/stream/source")
async def update_stream_source(update: StreamSourceUpdate):
    try:
        status = await stream_service.configure(update.url, update.label)
    except StreamSourceError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    await live_ws_manager.broadcast({"type": "stream_status", "data": status})
    return status


@app.delete("/api/stream/source")
async def clear_stream_source():
    status = await stream_service.clear()
    await live_ws_manager.broadcast({"type": "stream_status", "data": status})
    return status


@app.get("/api/stream/proxy/{token}")
async def proxy_stream(token: str, request: Request):
    try:
        remote = await stream_service.open_remote(token, request.headers.get("range", ""))
    except StreamSourceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Không thể kết nối tới nguồn phát") from exc

    upstream = remote.response
    content_type = upstream.headers.get("content-type", "application/octet-stream")
    upstream_url = str(upstream.url)

    if upstream.status_code >= 400:
        await remote.close()
        raise HTTPException(status_code=502, detail=f"Nguồn phát trả về HTTP {upstream.status_code}")

    if stream_service.is_hls_response(upstream_url, content_type):
        try:
            body = await upstream.aread()
            if len(body) > MAX_MANIFEST_BYTES:
                raise HTTPException(status_code=413, detail="Playlist HLS vượt quá giới hạn 2 MB")
            manifest = body.decode(upstream.encoding or "utf-8", errors="replace")
            rewritten = stream_service.rewrite_manifest(manifest, upstream_url)
        finally:
            await remote.close()
        return Response(
            content=rewritten,
            media_type="application/vnd.apple.mpegurl",
            headers={"Cache-Control": "no-store"},
        )

    response_headers = {}
    for header in ("content-length", "content-range", "accept-ranges", "cache-control", "etag", "last-modified", "content-encoding"):
        value = upstream.headers.get(header)
        if value:
            response_headers[header] = value

    return StreamingResponse(
        upstream.aiter_raw(),
        status_code=upstream.status_code,
        media_type=content_type,
        headers=response_headers,
        background=BackgroundTask(remote.close),
    )


# Products CRUD
@app.get("/api/products")
def list_products(db: Session = Depends(get_db)):
    return db.query(Product).all()


@app.post("/api/products")
def create_product(prod: ProductCreate, db: Session = Depends(get_db)):
    db_prod = Product(**prod.dict())
    db.add(db_prod)
    db.commit()
    db.refresh(db_prod)
    return db_prod


@app.delete("/api/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    db_prod = db.query(Product).filter(Product.id == product_id).first()
    if not db_prod:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(db_prod)
    db.commit()
    return {"status": "deleted"}


# Settings APIs
@app.get("/api/settings/ai")
def get_ai_settings():
    return {
        "provider": ai_service.provider,
        # Never send provider credentials back to the browser.
        "api_key": "",
        "has_api_key": bool(ai_service.api_key),
        "base_url": ai_service.base_url,
        "model": ai_service.model,
        "system_prompt": ai_service.system_prompt
    }


@app.post("/api/settings/ai")
def update_ai_settings(update: AISettingsUpdate):
    allowed_providers = {"openai", "openrouter", "ollama"}
    if update.provider not in allowed_providers:
        raise HTTPException(status_code=422, detail="Unsupported AI provider")

    parsed_url = urlparse(update.base_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.hostname:
        raise HTTPException(status_code=422, detail="Invalid AI base URL")

    hostname = parsed_url.hostname.lower()
    trusted_remote_hosts = {
        "openai": {"api.openai.com"},
        "openrouter": {"openrouter.ai"},
    }
    is_local_hostname = hostname in {"localhost", "host.docker.internal"}
    try:
        address = ipaddress.ip_address(hostname)
        is_private_address = (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_reserved
        )
    except ValueError:
        is_private_address = False

    if update.provider != "ollama" and (is_local_hostname or is_private_address):
        raise HTTPException(status_code=422, detail="Private AI base URLs are only allowed for Ollama")
    if update.provider != "ollama" and parsed_url.scheme != "https":
        raise HTTPException(status_code=422, detail="Remote AI providers must use HTTPS")
    if update.provider in trusted_remote_hosts and hostname not in trusted_remote_hosts[update.provider]:
        raise HTTPException(status_code=422, detail=f"Untrusted base URL for {update.provider}")
    if parsed_url.username or parsed_url.password or parsed_url.fragment:
        raise HTTPException(status_code=422, detail="AI base URL must not contain credentials or fragments")

    ai_service.provider = update.provider
    if update.clear_api_key:
        ai_service.api_key = ""
    elif update.api_key.strip():
        ai_service.api_key = update.api_key.strip()
    ai_service.base_url = update.base_url.rstrip("/")
    ai_service.model = update.model
    ai_service.set_system_prompt(update.system_prompt)
    save_runtime_settings({
        "ai.provider": ai_service.provider,
        "ai.api_key": ai_service.api_key,
        "ai.base_url": ai_service.base_url,
        "ai.model": ai_service.model,
        "ai.system_prompt": ai_service.system_prompt,
    })
    return {"status": "updated"}


class SceneSettingsUpdate(BaseModel):
    aspect_ratio: Literal["9:16", "16:9", "1:1"] = "9:16"
    avatar_x: int = Field(default=50, ge=0, le=100)
    avatar_y: int = Field(default=65, ge=0, le=100)
    avatar_scale: int = Field(default=100, ge=25, le=300)
    avatar_visible: bool = True
    avatar_style: Literal["default", "anime", "corporate", "cyberpunk"] = "default"
    avatar_mode: Literal["builtin", "video"] = "builtin"
    avatar_media_url: str = Field(default="", max_length=500)
    avatar_fit: Literal["contain", "cover"] = "contain"
    video_media_url: str = Field(default="", max_length=500)
    video_name: str = Field(default="", max_length=255)
    video_x: int = Field(default=50, ge=0, le=100)
    video_y: int = Field(default=50, ge=0, le=100)
    video_width: int = Field(default=100, ge=1, le=300)
    video_height: int = Field(default=100, ge=1, le=300)
    video_rotation: int = Field(default=0, ge=-180, le=180)
    video_fit: Literal["contain", "cover"] = "contain"
    video_visible: bool = True
    caption_x: int = Field(default=50, ge=0, le=100)
    caption_y: int = Field(default=88, ge=0, le=100)
    caption_visible: bool = True
    caption_font_size: int = Field(default=18, ge=8, le=96)
    caption_text_color: str = Field(default="#ffffff", max_length=32)
    caption_bg_color: str = Field(default="rgba(15, 23, 42, 0.85)", max_length=64)
    caption_preset: Literal["capcut_yellow", "cyberpunk", "minimal_dark", "default"] = "capcut_yellow"
    bg_mode: Literal["transparent", "chroma_green", "dark_studio"] = "transparent"


MAX_AVATAR_VIDEO_BYTES = 50 * 1024 * 1024
ALLOWED_AVATAR_VIDEO_TYPES = {
    "video/mp4": ".mp4",
    "video/webm": ".webm",
}


@app.post("/api/media/upload")
@app.post("/api/avatar/upload")
async def upload_avatar_video(video: UploadFile = File(...)):
    extension = ALLOWED_AVATAR_VIDEO_TYPES.get(video.content_type or "")
    if extension is None:
        raise HTTPException(status_code=415, detail="Chỉ hỗ trợ video MP4 hoặc WebM")

    stored_name = f"{uuid.uuid4().hex}{extension}"
    stored_path = os.path.abspath(os.path.join(AVATAR_DIR, stored_name))
    avatar_root = os.path.abspath(AVATAR_DIR)
    if os.path.commonpath([stored_path, avatar_root]) != avatar_root:
        raise HTTPException(status_code=400, detail="Tên tệp không hợp lệ")

    total_size = 0
    signature = b""
    try:
        with open(stored_path, "wb") as output:
            while chunk := await video.read(1024 * 1024):
                total_size += len(chunk)
                if total_size > MAX_AVATAR_VIDEO_BYTES:
                    raise HTTPException(status_code=413, detail="Video vượt quá giới hạn 50 MB")
                if len(signature) < 16:
                    signature += chunk[:16 - len(signature)]
                output.write(chunk)

        is_mp4 = extension == ".mp4" and len(signature) >= 8 and signature[4:8] == b"ftyp"
        is_webm = extension == ".webm" and signature.startswith(b"\x1a\x45\xdf\xa3")
        if total_size == 0 or not (is_mp4 or is_webm):
            raise HTTPException(status_code=422, detail="Nội dung tệp không phải video MP4/WebM hợp lệ")
    except Exception:
        if os.path.exists(stored_path):
            os.remove(stored_path)
        raise
    finally:
        await video.close()

    return {
        "status": "ok",
        "media_url": f"/static/avatars/{stored_name}",
        "size": total_size,
    }


@app.get("/api/settings/scene")
def get_scene_settings(db: Session = Depends(get_db)):
    setting = db.query(SceneSetting).first()
    if not setting:
        setting = SceneSetting()
        db.add(setting)
        db.commit()
        db.refresh(setting)
    return {
        "aspect_ratio": setting.aspect_ratio,
        "avatar_x": setting.avatar_x,
        "avatar_y": setting.avatar_y,
        "avatar_scale": setting.avatar_scale,
        "avatar_visible": setting.avatar_visible if setting.avatar_visible is not None else True,
        "avatar_style": setting.avatar_style,
        "avatar_mode": setting.avatar_mode or "builtin",
        "avatar_media_url": setting.avatar_media_url or "",
        "avatar_fit": setting.avatar_fit or "contain",
        "video_media_url": setting.video_media_url or "",
        "video_name": setting.video_name or "",
        "video_x": setting.video_x if setting.video_x is not None else 50,
        "video_y": setting.video_y if setting.video_y is not None else 50,
        "video_width": setting.video_width if setting.video_width is not None else 100,
        "video_height": setting.video_height if setting.video_height is not None else 100,
        "video_rotation": setting.video_rotation if setting.video_rotation is not None else 0,
        "video_fit": setting.video_fit or "contain",
        "video_visible": setting.video_visible if setting.video_visible is not None else True,
        "caption_x": setting.caption_x,
        "caption_y": setting.caption_y,
        "caption_visible": setting.caption_visible if setting.caption_visible is not None else True,
        "caption_font_size": setting.caption_font_size,
        "caption_text_color": setting.caption_text_color,
        "caption_bg_color": setting.caption_bg_color,
        "caption_preset": setting.caption_preset,
        "bg_mode": setting.bg_mode
    }


@app.post("/api/settings/scene")
async def update_scene_settings(update: SceneSettingsUpdate, db: Session = Depends(get_db)):
    setting = db.query(SceneSetting).first()
    if not setting:
        setting = SceneSetting()
        db.add(setting)

    setting.aspect_ratio = update.aspect_ratio
    setting.avatar_x = update.avatar_x
    setting.avatar_y = update.avatar_y
    setting.avatar_scale = update.avatar_scale
    setting.avatar_visible = update.avatar_visible
    setting.avatar_style = update.avatar_style
    setting.avatar_mode = update.avatar_mode
    setting.avatar_media_url = update.avatar_media_url
    setting.avatar_fit = update.avatar_fit
    setting.video_media_url = update.video_media_url
    setting.video_name = update.video_name
    setting.video_x = update.video_x
    setting.video_y = update.video_y
    setting.video_width = update.video_width
    setting.video_height = update.video_height
    setting.video_rotation = update.video_rotation
    setting.video_fit = update.video_fit
    setting.video_visible = update.video_visible
    setting.caption_x = update.caption_x
    setting.caption_y = update.caption_y
    setting.caption_visible = update.caption_visible
    setting.caption_font_size = update.caption_font_size
    setting.caption_text_color = update.caption_text_color
    setting.caption_bg_color = update.caption_bg_color
    setting.caption_preset = update.caption_preset
    setting.bg_mode = update.bg_mode

    db.commit()
    cleanup_unreferenced_media()

    config_data = {
        "type": "scene_config_update",
        "data": update.dict()
    }
    await scene_ws_manager.broadcast(config_data)
    return {"status": "updated", "config": update.dict()}


@app.get("/api/settings/tts")
def get_tts_settings():
    return {
        "voice": tts_service.voice,
        "rate": tts_service.rate,
        "pitch": tts_service.pitch
    }


@app.post("/api/settings/tts")
def update_tts_settings(update: TTSSettingsUpdate):
    tts_service.voice = update.voice
    tts_service.rate = update.rate
    tts_service.pitch = update.pitch
    save_runtime_settings({
        "tts.voice": tts_service.voice,
        "tts.rate": tts_service.rate,
        "tts.pitch": tts_service.pitch,
    })
    return {"status": "updated"}


@app.post("/api/tts/preview")
async def preview_tts(req: TestTTSRequest = TestTTSRequest()):
    text = req.text or "Xin chào, hệ thống giọng đọc AI livestream đã sẵn sàng!"
    audio_url = await tts_service.generate_speech(text)
    if not audio_url:
        raise HTTPException(status_code=502, detail="Không thể tạo giọng đọc TTS")
    return {"status": "ok", "audio_url": audio_url, "text": text}


@app.post("/api/tts/test")
async def test_tts(req: TestTTSRequest = TestTTSRequest()):
    text = req.text or "Xin chào, hệ thống giọng đọc AI livestream đã sẵn sàng!"
    job = await interaction_queue.create_job(
        event_type="tts_test",
        user_id="system_test",
        user_name="Hệ thống Test",
        user_message=text,
    )
    if job["status"] == "skipped":
        raise HTTPException(status_code=429, detail="Interaction queue is full")
    await interaction_queue.mark_ai_processing(job["id"])
    job = await interaction_queue.set_ai_reply_and_enqueue(job["id"], text)
    return {"status": "accepted", "job": job}


@app.get("/api/logs")
def get_logs(limit: int = Query(default=50, ge=1, le=500), db: Session = Depends(get_db)):
    return db.query(LiveLog).order_by(LiveLog.id.desc()).limit(limit).all()


# WebSockets
@app.websocket("/ws/live")
async def websocket_live_endpoint(websocket: WebSocket):
    if not websocket_origin_allowed(websocket):
        await websocket.close(code=1008, reason="WebSocket origin is not allowed")
        return
    renderer_id = await live_ws_manager.connect(websocket)
    await live_ws_manager.send_to(renderer_id, {
        "type": "interaction_snapshot",
        "data": {
            "renderer_id": renderer_id,
            "queue": interaction_queue.status(),
            "jobs": interaction_queue.list_jobs(limit=50),
        },
    })
    try:
        while True:
            message = await websocket.receive_json()
            if message.get("type") == "playback_ack":
                try:
                    job = await interaction_queue.acknowledge_playback(
                        job_id=message.get("job_id", ""),
                        playback_id=message.get("playback_id", ""),
                        state=message.get("state", ""),
                        source="live",
                        error=message.get("error", ""),
                        renderer_id=renderer_id,
                    )
                    await live_ws_manager.send_to(
                        renderer_id,
                        {"type": "playback_ack_accepted", "data": job},
                    )
                except InteractionQueueError as exc:
                    await live_ws_manager.send_to(
                        renderer_id,
                        {"type": "playback_ack_rejected", "error": str(exc)},
                    )
    except WebSocketDisconnect:
        pass
    finally:
        live_ws_manager.disconnect(websocket)
        await interaction_queue.renderer_disconnected("live", renderer_id)


@app.websocket("/ws/scene")
async def websocket_scene_endpoint(websocket: WebSocket):
    if not websocket_origin_allowed(websocket):
        await websocket.close(code=1008, reason="WebSocket origin is not allowed")
        return
    renderer_id = await scene_ws_manager.connect(websocket)
    await scene_ws_manager.send_to(renderer_id, {
        "type": "renderer_hello",
        "renderer_id": renderer_id,
        "renderer_type": "scene",
    })
    try:
        while True:
            message = await websocket.receive_json()
            if message.get("type") == "playback_ack":
                try:
                    job = await interaction_queue.acknowledge_playback(
                        job_id=message.get("job_id", ""),
                        playback_id=message.get("playback_id", ""),
                        state=message.get("state", ""),
                        source="scene",
                        error=message.get("error", ""),
                        renderer_id=renderer_id,
                    )
                    await scene_ws_manager.send_to(
                        renderer_id,
                        {"type": "playback_ack_accepted", "data": job},
                    )
                except InteractionQueueError as exc:
                    await scene_ws_manager.send_to(
                        renderer_id,
                        {"type": "playback_ack_rejected", "error": str(exc)},
                    )
    except WebSocketDisconnect:
        pass
    finally:
        scene_ws_manager.disconnect(websocket)
        await interaction_queue.renderer_disconnected("scene", renderer_id)


# Keep this final so API, WebSocket and backend static routes take precedence.
FRONTEND_DIST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))
if os.path.isfile(os.path.join(FRONTEND_DIST_DIR, "index.html")):
    app.mount("/", SPAStaticFiles(directory=FRONTEND_DIST_DIR, html=True), name="frontend")
