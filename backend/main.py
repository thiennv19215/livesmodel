import os
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import settings
from database import init_db, get_db, Product, TriggerRule, LiveLog
from services.tiktok_connector import TikTokConnector
from services.trigger_engine import TriggerEngine
from services.product_matcher import ProductMatcher
from services.ai_service import AIService
from services.tts_service import TTSService
from services.shop_automation import ShopAutomation

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("livestream_backend")

# Initialize DB tables
init_db()

app = FastAPI(title=settings.APP_NAME)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure static directories exist
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
AUDIO_DIR = os.path.join(STATIC_DIR, "audio")
SCENE_DIR = os.path.join(STATIC_DIR, "scene")
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(SCENE_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# WebSocket Connection Managers
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

live_ws_manager = ConnectionManager()
scene_ws_manager = ConnectionManager()

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

# Callback for TikTok Events
async def handle_tiktok_event(event: Dict[str, Any]):
    logger.info(f"Incoming TikTok Event: {event}")
    event_type = event.get("type", "chat")
    user_name = event.get("user_name", "Khán giả")
    user_id = event.get("user_id", user_name)

    # Broadcast raw event to Live Console UI
    await live_ws_manager.broadcast({"type": "raw_event", "data": event})

    if event_type == "chat":
        comment = event.get("comment", "")
        # Evaluate comment through 9-step filter pipeline & cooldowns
        should_process, cleaned_comment, reason = trigger_engine.evaluate_comment(user_name, user_id, comment)

        if not should_process:
            logger.info(f"Comment from '{user_name}' filtered out. Reason: {reason}")
            await live_ws_manager.broadcast({
                "type": "event_filtered",
                "user_name": user_name,
                "comment": comment,
                "reason": reason
            })
            return

        # Match Product using deterministic 1000-point algorithm
        from database import SessionLocal
        db = SessionLocal()
        try:
            matcher = ProductMatcher(db, score_threshold=160)
            product, score = matcher.match_comment(cleaned_comment)
            product_ctx = None
            if product:
                product_ctx = f"Sản phẩm: {product.name}, Giá: {product.price}. Điểm nổi bật: {product.selling_points}."

            # Generate AI Reply
            ai_reply = await ai_service.generate_response(user_name, cleaned_comment, product_ctx, event_type="chat")

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
                "user_name": user_name,
                "user_message": comment,
                "ai_reply": ai_reply,
                "matched_product": product.name if product else None,
                "match_score": score
            }
            await live_ws_manager.broadcast(event_response)

            # Enqueue for TTS Speech & Scene Broadcast
            await tts_service.enqueue(ai_reply, user_name)

        finally:
            db.close()

    elif event_type in ["gift", "follow", "share", "member", "join"]:
        # Handle non-chat events with templates
        ai_reply = await ai_service.generate_response(user_name, "", event_type=event_type)
        user_msg = "Vừa vào phòng livestream" if event_type in ["member", "join"] else f"Sự kiện: {event_type}"

        from database import SessionLocal
        db = SessionLocal()
        try:
            log_entry = LiveLog(
                event_type=event_type,
                user_name=user_name,
                user_message=user_msg,
                ai_reply=ai_reply,
                status="processed"
            )
            db.add(log_entry)
            db.commit()
        finally:
            db.close()

        await live_ws_manager.broadcast({
            "type": "ai_response",
            "user_name": user_name,
            "user_message": user_msg,
            "ai_reply": ai_reply
        })
        await tts_service.enqueue(ai_reply, user_name)

# Initialize TikTok Connector
tiktok_connector = TikTokConnector(event_callback=handle_tiktok_event)

# Callback when TTS starts playing audio -> send to OBS scene overlay and Live Console
async def broadcast_tts_to_scene(tts_data: Dict[str, Any]):
    await scene_ws_manager.broadcast(tts_data)
    await live_ws_manager.broadcast(tts_data)

@app.on_event("startup")
async def startup_event():
    # Start TTS queue processing background task
    asyncio.create_task(tts_service.start_queue_worker(broadcast_tts_to_scene))
    logger.info("Application startup complete.")

# Pydantic Schemas
class ProductCreate(BaseModel):
    name: str
    keywords: str = ""
    price: str = ""
    selling_points: str = ""
    custom_script: str = ""
    product_link: str = ""

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
    username: str

class AISettingsUpdate(BaseModel):
    provider: str
    api_key: str
    base_url: str
    model: str
    system_prompt: str

class TTSSettingsUpdate(BaseModel):
    voice: str
    rate: str
    pitch: str

class TestTTSRequest(BaseModel):
    text: Optional[str] = "Xin chào, hệ thống giọng đọc AI livestream đã sẵn sàng!"

class ManualChatRequest(BaseModel):
    user_name: str
    comment: str

class ManualEventRequest(BaseModel):
    user_name: str
    event_type: str = "member"

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
    await handle_tiktok_event({
        "type": "chat",
        "user_name": req.user_name,
        "comment": req.comment,
        "user_id": f"user_{hash(req.user_name) % 10000}"
    })
    return {"status": "triggered"}

@app.post("/api/manual_event")
async def send_manual_event(req: ManualEventRequest):
    await handle_tiktok_event({
        "type": req.event_type,
        "user_name": req.user_name,
        "user_id": f"user_{hash(req.user_name) % 10000}"
    })
    return {"status": "triggered"}

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
        "api_key": ai_service.api_key,
        "base_url": ai_service.base_url,
        "model": ai_service.model,
        "system_prompt": ai_service.system_prompt
    }

@app.post("/api/settings/ai")
def update_ai_settings(update: AISettingsUpdate):
    ai_service.provider = update.provider
    ai_service.api_key = update.api_key
    ai_service.base_url = update.base_url
    ai_service.model = update.model
    ai_service.set_system_prompt(update.system_prompt)
    return {"status": "updated"}

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
    return {"status": "updated"}

@app.post("/api/tts/test")
async def test_tts(req: TestTTSRequest = TestTTSRequest()):
    text = req.text or "Xin chào, hệ thống giọng đọc AI livestream đã sẵn sàng!"
    audio_url = await tts_service.generate_speech(text)
    if not audio_url:
        raise HTTPException(status_code=500, detail="Không thể tạo giọng đọc TTS")
    
    tts_data = {
        "type": "tts_play",
        "text": text,
        "user_name": "Hệ thống Test",
        "audio_url": audio_url
    }
    await broadcast_tts_to_scene(tts_data)
    return {"status": "ok", "audio_url": audio_url, "text": text}

@app.get("/api/logs")
def get_logs(limit: int = 50, db: Session = Depends(get_db)):
    return db.query(LiveLog).order_by(LiveLog.id.desc()).limit(limit).all()

# WebSockets
@app.websocket("/ws/live")
async def websocket_live_endpoint(websocket: WebSocket):
    await live_ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        live_ws_manager.disconnect(websocket)

@app.websocket("/ws/scene")
async def websocket_scene_endpoint(websocket: WebSocket):
    await scene_ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        scene_ws_manager.disconnect(websocket)
