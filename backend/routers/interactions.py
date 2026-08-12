import uuid
from typing import Any, Dict, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from services.interaction_queue import InteractionJobNotFound, InteractionQueueError


class TikTokConnectRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)


class ManualChatRequest(BaseModel):
    user_name: str = Field(min_length=1, max_length=255)
    comment: str = Field(min_length=1, max_length=2000)


class ManualEventRequest(BaseModel):
    user_name: str = Field(min_length=1, max_length=255)
    event_type: Literal["gift", "follow", "share", "member", "join"] = "member"


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


def create_interaction_router(*, tiktok_connector, handle_event, interaction_queue) -> APIRouter:
    router = APIRouter()

    @router.post("/api/tiktok/connect")
    async def connect_tiktok(req: TikTokConnectRequest):
        success = await tiktok_connector.connect(req.username)
        return {"status": "connected" if success else "failed", "username": req.username}

    @router.post("/api/tiktok/disconnect")
    async def disconnect_tiktok():
        await tiktok_connector.disconnect()
        return {"status": "disconnected"}

    @router.get("/api/tiktok/status")
    def get_tiktok_status():
        return {"is_connected": tiktok_connector.is_connected, "username": tiktok_connector.username}

    @router.post("/api/manual_chat")
    async def send_manual_chat(req: ManualChatRequest):
        job = await handle_event({
            "type": "chat",
            "user_name": req.user_name,
            "comment": req.comment,
            "user_id": f"user_{hash(req.user_name) % 10000}",
        })
        return {"status": "accepted", "job": job}

    @router.post("/api/manual_event")
    async def send_manual_event(req: ManualEventRequest):
        job = await handle_event({
            "type": req.event_type,
            "user_name": req.user_name,
            "user_id": f"user_{hash(req.user_name) % 10000}",
        })
        return {"status": "accepted", "job": job}

    @router.post("/api/interaction-jobs", status_code=202)
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
        job = await handle_event(event)
        if job and job["status"] == "skipped" and job["decision_reason"] == "queue_full":
            raise HTTPException(status_code=429, detail={"message": "Interaction queue is full", "job": job})
        return {"status": "accepted", "job": job}

    @router.get("/api/interaction-jobs")
    def list_interaction_jobs(
        limit: int = Query(default=50, ge=1, le=500),
        status: str = Query(default="", max_length=50),
    ):
        return {"jobs": interaction_queue.list_jobs(limit=limit, status=status)}

    @router.get("/api/interaction-jobs/{job_id}")
    def get_interaction_job(job_id: str):
        try:
            return interaction_queue.get_job(job_id)
        except InteractionJobNotFound as exc:
            raise HTTPException(status_code=404, detail="Interaction job not found") from exc

    @router.post("/api/interaction-jobs/{job_id}/playback")
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

    @router.post("/api/interaction-jobs/{job_id}/cancel")
    async def cancel_interaction_job(job_id: str):
        try:
            return await interaction_queue.cancel(job_id)
        except InteractionJobNotFound as exc:
            raise HTTPException(status_code=404, detail="Interaction job not found") from exc
        except InteractionQueueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @router.post("/api/interaction-jobs/{job_id}/retry")
    async def retry_interaction_job(job_id: str):
        try:
            return await interaction_queue.retry(job_id)
        except InteractionJobNotFound as exc:
            raise HTTPException(status_code=404, detail="Interaction job not found") from exc
        except InteractionQueueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @router.get("/api/interaction-queue")
    def get_interaction_queue_status():
        return interaction_queue.status()

    @router.post("/api/interaction-queue/skip-current")
    async def skip_current_interaction():
        job = await interaction_queue.skip_current()
        return {"job": job, **interaction_queue.status()}

    @router.post("/api/interaction-queue/clear")
    async def clear_interaction_queue(req: QueueClearRequest = QueueClearRequest()):
        return await interaction_queue.clear(include_current=req.include_current)

    return router
