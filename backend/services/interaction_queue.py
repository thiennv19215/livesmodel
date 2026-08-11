import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set, Tuple, Union

from sqlalchemy.orm import Session

try:
    from database import InteractionJob
except ModuleNotFoundError:  # Package import path used by unit tests.
    from backend.database import InteractionJob


logger = logging.getLogger(__name__)

ACTIVE_STATUSES = {
    "received",
    "ai_processing",
    "queued",
    "tts_processing",
    "ready",
    "playing",
}
TERMINAL_STATUSES = {"done", "skipped", "cancelled", "error"}
ALLOWED_TRANSITIONS = {
    "received": {"ai_processing", "skipped", "cancelled", "error"},
    "ai_processing": {"queued", "skipped", "cancelled", "error"},
    "queued": {"tts_processing", "skipped", "cancelled", "error"},
    "tts_processing": {"ready", "cancelled", "error"},
    "ready": {"playing", "done", "cancelled", "error"},
    "playing": {"done", "cancelled", "error"},
    "done": set(),
    "skipped": set(),
    "cancelled": {"queued"},
    "error": {"queued"},
}


class InteractionQueueError(RuntimeError):
    pass


class InteractionJobNotFound(InteractionQueueError):
    pass


class InvalidJobTransition(InteractionQueueError):
    pass


@dataclass
class PlaybackWaiter:
    playback_id: str
    owner: str
    renderer_id: str = ""
    terminal_event: asyncio.Event = field(default_factory=asyncio.Event)
    outcome: str = ""


def serialize_job(job: InteractionJob) -> Dict[str, Any]:
    def iso(value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() + "Z" if value else None

    return {
        "id": job.id,
        "event_type": job.event_type,
        "user_id": job.user_id or "",
        "user_name": job.user_name or "",
        "user_message": job.user_message or "",
        "status": job.status,
        "decision_reason": job.decision_reason or "",
        "ai_reply": job.ai_reply or "",
        "audio_url": job.audio_url or "",
        "playback_id": job.playback_id or "",
        "playback_owner": job.playback_owner or "",
        "error": job.error or "",
        "retry_count": job.retry_count or 0,
        "created_at": iso(job.created_at),
        "updated_at": iso(job.updated_at),
        "started_at": iso(job.started_at),
        "finished_at": iso(job.finished_at),
    }


class InteractionQueueService:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        tts_service: Any,
        max_queue_size: int = 100,
        tts_timeout_seconds: float = 120.0,
        playback_timeout_seconds: float = 120.0,
    ) -> None:
        self.session_factory = session_factory
        self.tts_service = tts_service
        self.max_queue_size = max_queue_size
        self.tts_timeout_seconds = tts_timeout_seconds
        self.playback_timeout_seconds = playback_timeout_seconds
        # Admission is limited by persisted non-terminal jobs. The physical queue
        # stays unbounded so cancelled tombstones cannot consume capacity.
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self._enqueued_ids: Set[str] = set()
        self.worker_task: Optional[asyncio.Task] = None
        self.is_running = False
        self.current_job_id = ""
        self.current_cancel_event: Optional[asyncio.Event] = None
        self.playback_waiters: Dict[str, PlaybackWaiter] = {}
        self.broadcast_callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None
        self.state_callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None
        self.owner_selector: Optional[
            Callable[[], Union[str, Tuple[str, str]]]
        ] = None
        self._lock = asyncio.Lock()
        self._attempt_lock = asyncio.Lock()

    async def start(
        self,
        broadcast_callback: Callable[[Dict[str, Any]], Awaitable[None]],
        state_callback: Callable[[Dict[str, Any]], Awaitable[None]],
        owner_selector: Callable[[], Union[str, Tuple[str, str]]],
    ) -> None:
        if self.worker_task and not self.worker_task.done():
            return
        self.broadcast_callback = broadcast_callback
        self.state_callback = state_callback
        self.owner_selector = owner_selector
        self._mark_interrupted_jobs()
        self.is_running = True
        self.worker_task = asyncio.create_task(self._run_worker(), name="interaction-queue-worker")

    async def stop(self) -> None:
        self.is_running = False
        if self.current_job_id:
            await self._cancel_current("backend_shutdown")
        if self.worker_task and not self.worker_task.done():
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
        self.worker_task = None

    async def create_job(
        self,
        event_type: str,
        user_id: str,
        user_name: str,
        user_message: str,
    ) -> Dict[str, Any]:
        async with self._lock:
            db = self.session_factory()
            try:
                active_count = db.query(InteractionJob).filter(InteractionJob.status.in_(ACTIVE_STATUSES)).count()
                queue_full = active_count >= self.max_queue_size
                now = datetime.utcnow()
                job = InteractionJob(
                    id=str(uuid.uuid4()),
                    event_type=event_type,
                    user_id=user_id,
                    user_name=user_name,
                    user_message=user_message,
                    status="skipped" if queue_full else "received",
                    decision_reason="queue_full" if queue_full else "",
                    created_at=now,
                    updated_at=now,
                    finished_at=now if queue_full else None,
                )
                db.add(job)
                db.commit()
                db.refresh(job)
                payload = serialize_job(job)
            finally:
                db.close()
        await self._notify(payload)
        return payload

    async def mark_ai_processing(self, job_id: str) -> Dict[str, Any]:
        return await self._transition(job_id, "ai_processing")

    async def mark_skipped(self, job_id: str, reason: str) -> Dict[str, Any]:
        return await self._transition(job_id, "skipped", decision_reason=reason)

    async def mark_error(self, job_id: str, error: str) -> Dict[str, Any]:
        return await self._force_terminal(job_id, "error", error)

    async def set_ai_reply_and_enqueue(self, job_id: str, ai_reply: str) -> Dict[str, Any]:
        return await self._enqueue(
            job_id,
            expected_statuses={"ai_processing"},
            updates={"ai_reply": ai_reply, "error": ""},
        )

    async def acknowledge_playback(
        self,
        job_id: str,
        playback_id: str,
        state: str,
        source: str,
        error: str = "",
        renderer_id: str = "",
    ) -> Dict[str, Any]:
        if state not in {"started", "ended", "failed"}:
            raise InteractionQueueError("Unsupported playback state")
        current = self.get_job(job_id)
        if current["status"] in TERMINAL_STATUSES:
            if current["playback_id"] == playback_id and current["playback_owner"] == source:
                return current
            raise InteractionQueueError("Playback lease is missing or expired")

        async with self._attempt_lock:
            waiter = self.playback_waiters.get(job_id)
            if not waiter or waiter.playback_id != playback_id:
                raise InteractionQueueError("Playback lease is missing or expired")
            if source != waiter.owner:
                raise InteractionQueueError(f"Playback acknowledgement must come from '{waiter.owner}'")
            if waiter.renderer_id and renderer_id != waiter.renderer_id:
                raise InteractionQueueError("Playback acknowledgement came from a non-owner renderer")

            current = self.get_job(job_id)
            if current["status"] in TERMINAL_STATUSES:
                return current

            if state == "started":
                if current["status"] == "ready":
                    return await self._transition(
                        job_id,
                        "playing",
                        expected_statuses={"ready"},
                        started_at=datetime.utcnow(),
                    )
                if current["status"] == "playing":
                    return current
                raise InvalidJobTransition(f"Cannot start playback from {current['status']}")

            if waiter.terminal_event.is_set():
                return self.get_job(job_id)

            if state == "ended":
                if current["status"] != "playing":
                    raise InvalidJobTransition("Playback must be started before it can end")
                result = await self._transition(
                    job_id,
                    "done",
                    expected_statuses={"playing"},
                    finished_at=datetime.utcnow(),
                )
                waiter.outcome = "done"
            else:
                result = await self._force_terminal(job_id, "error", error or "playback_failed")
                waiter.outcome = "error"
            waiter.terminal_event.set()
            return result

    async def skip_current(self) -> Optional[Dict[str, Any]]:
        return await self._cancel_current("skipped_by_user")

    async def cancel(self, job_id: str) -> Dict[str, Any]:
        current = self.get_job(job_id)
        if current["status"] in TERMINAL_STATUSES:
            return current
        if job_id == self.current_job_id:
            result = await self._cancel_current("cancelled_by_user")
            if result:
                return result
        return await self._force_terminal(job_id, "cancelled", "cancelled_by_user")

    async def clear(self, include_current: bool = False) -> Dict[str, Any]:
        cancelled_ids: List[str] = []
        while True:
            try:
                job_id = self.queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            try:
                await self._force_terminal(job_id, "cancelled", "queue_cleared")
                cancelled_ids.append(job_id)
            finally:
                self.queue.task_done()

        if include_current and self.current_job_id:
            current = await self.skip_current()
            if current:
                cancelled_ids.append(current["id"])
        return {"cancelled_job_ids": cancelled_ids, **self.status()}

    async def retry(self, job_id: str) -> Dict[str, Any]:
        current = self.get_job(job_id)
        if current["status"] not in {"error", "cancelled"}:
            raise InvalidJobTransition("Only errored or cancelled jobs can be retried")
        if not current["ai_reply"]:
            raise InvalidJobTransition("Job has no AI reply to synthesize again")
        return await self._enqueue(
            job_id,
            expected_statuses={"error", "cancelled"},
            check_capacity=True,
            updates={
                "error": "",
                "decision_reason": "retry_requested",
                "retry_count": current["retry_count"] + 1,
                "finished_at": None,
                "started_at": None,
                "playback_id": "",
                "playback_owner": "",
                "audio_url": "",
            },
        )

    def get_job(self, job_id: str) -> Dict[str, Any]:
        db = self.session_factory()
        try:
            job = db.query(InteractionJob).filter(InteractionJob.id == job_id).first()
            if not job:
                raise InteractionJobNotFound(job_id)
            return serialize_job(job)
        finally:
            db.close()

    def list_jobs(self, limit: int = 50, status: str = "") -> List[Dict[str, Any]]:
        db = self.session_factory()
        try:
            query = db.query(InteractionJob)
            if status:
                query = query.filter(InteractionJob.status == status)
            jobs = query.order_by(InteractionJob.created_at.desc()).limit(limit).all()
            return [serialize_job(job) for job in jobs]
        finally:
            db.close()

    def status(self) -> Dict[str, Any]:
        pending_count = len(self._enqueued_ids)
        return {
            "is_running": self.is_running,
            "current_job_id": self.current_job_id,
            "active_job_id": self.current_job_id,
            "queued_count": pending_count,
            "pending_count": pending_count,
            "max_queue_size": self.max_queue_size,
            "capacity": self.max_queue_size,
            "playback_waiting": bool(self.current_job_id in self.playback_waiters),
        }

    async def _run_worker(self) -> None:
        while self.is_running:
            try:
                job_id = await self.queue.get()
            except asyncio.CancelledError:
                break

            self._enqueued_ids.discard(job_id)
            self.current_job_id = job_id
            self.current_cancel_event = asyncio.Event()
            try:
                job = self.get_job(job_id)
                if job["status"] != "queued":
                    continue
                await self._transition(job_id, "tts_processing")

                tts_task = asyncio.create_task(self.tts_service.generate_speech(job["ai_reply"]))
                cancel_task = asyncio.create_task(self.current_cancel_event.wait())
                done, pending = await asyncio.wait(
                    {tts_task, cancel_task},
                    timeout=self.tts_timeout_seconds,
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for pending_task in pending:
                    pending_task.cancel()
                if pending:
                    await asyncio.gather(*pending, return_exceptions=True)

                if cancel_task in done:
                    tts_task.cancel()
                    try:
                        await tts_task
                    except asyncio.CancelledError:
                        pass
                    continue
                if tts_task not in done:
                    await self._force_terminal(job_id, "error", "tts_generation_timeout")
                    continue

                audio_url = tts_task.result()
                if not audio_url:
                    await self._force_terminal(job_id, "error", "tts_generation_failed")
                    continue

                # A cancel can land just after TTS completes. Never dispatch audio
                # unless the persisted job is still the active attempt.
                if self.get_job(job_id)["status"] != "tts_processing":
                    continue

                selected_owner = self.owner_selector() if self.owner_selector else ""
                if isinstance(selected_owner, tuple):
                    owner, renderer_id = selected_owner
                else:
                    owner, renderer_id = selected_owner, ""
                if owner not in {"scene", "live"}:
                    await self._force_terminal(job_id, "error", "no_playback_client_connected")
                    continue

                playback_id = str(uuid.uuid4())
                waiter = PlaybackWaiter(
                    playback_id=playback_id,
                    owner=owner,
                    renderer_id=renderer_id,
                )
                async with self._attempt_lock:
                    if self.get_job(job_id)["status"] != "tts_processing":
                        continue
                    self.playback_waiters[job_id] = waiter
                    await self._transition(
                        job_id,
                        "ready",
                        expected_statuses={"tts_processing"},
                        audio_url=audio_url,
                        playback_id=playback_id,
                        playback_owner=owner,
                    )
                    if not self.broadcast_callback:
                        await self._force_terminal(job_id, "error", "playback_broadcast_unavailable")
                        continue

                    await self.broadcast_callback({
                        "type": "tts_play",
                        "job_id": job_id,
                        "playback_id": playback_id,
                        "playback_owner": owner,
                        "playback_renderer_id": renderer_id,
                        "text": job["ai_reply"],
                        "user_name": job["user_name"],
                        "audio_url": audio_url,
                    })
                try:
                    await asyncio.wait_for(waiter.terminal_event.wait(), timeout=self.playback_timeout_seconds)
                except asyncio.TimeoutError:
                    async with self._attempt_lock:
                        current = self.get_job(job_id)
                        if current["status"] not in TERMINAL_STATUSES:
                            await self._send_stop(current)
                            await self._force_terminal(job_id, "error", "playback_ack_timeout")
                            waiter.outcome = "error"
                            waiter.terminal_event.set()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("Interaction queue job %s failed", job_id)
                try:
                    await self._force_terminal(job_id, "error", str(exc))
                except Exception:
                    logger.exception("Unable to mark interaction job %s as failed", job_id)
            finally:
                self.playback_waiters.pop(job_id, None)
                self.current_job_id = ""
                self.current_cancel_event = None
                self.queue.task_done()
                await self._notify_queue()

    async def _transition(
        self,
        job_id: str,
        status: str,
        expected_statuses: Optional[Set[str]] = None,
        **updates: Any,
    ) -> Dict[str, Any]:
        async with self._lock:
            db = self.session_factory()
            try:
                job = db.query(InteractionJob).filter(InteractionJob.id == job_id).first()
                if not job:
                    raise InteractionJobNotFound(job_id)
                if expected_statuses is not None and job.status not in expected_statuses:
                    expected = ", ".join(sorted(expected_statuses))
                    raise InvalidJobTransition(f"Expected {expected}; found {job.status}")
                if status != job.status and status not in ALLOWED_TRANSITIONS.get(job.status, set()):
                    raise InvalidJobTransition(f"Cannot transition {job.status} -> {status}")
                job.status = status
                for key, value in updates.items():
                    setattr(job, key, value)
                job.updated_at = datetime.utcnow()
                if status in TERMINAL_STATUSES and job.finished_at is None:
                    job.finished_at = datetime.utcnow()
                db.commit()
                db.refresh(job)
                payload = serialize_job(job)
            finally:
                db.close()
        await self._notify(payload)
        return payload

    async def _force_terminal(self, job_id: str, status: str, reason: str) -> Dict[str, Any]:
        if status not in {"cancelled", "error", "skipped"}:
            raise InteractionQueueError("Invalid terminal status")
        async with self._lock:
            db = self.session_factory()
            try:
                job = db.query(InteractionJob).filter(InteractionJob.id == job_id).first()
                if not job:
                    raise InteractionJobNotFound(job_id)
                if job.status in TERMINAL_STATUSES:
                    return serialize_job(job)
                if status not in ALLOWED_TRANSITIONS.get(job.status, set()):
                    raise InvalidJobTransition(f"Cannot transition {job.status} -> {status}")
                job.status = status
                job.finished_at = datetime.utcnow()
                job.updated_at = datetime.utcnow()
                if status == "skipped":
                    job.decision_reason = reason
                else:
                    job.error = reason
                db.commit()
                db.refresh(job)
                payload = serialize_job(job)
                self._enqueued_ids.discard(job_id)
            finally:
                db.close()
        await self._notify(payload)
        return payload

    async def _enqueue(
        self,
        job_id: str,
        expected_statuses: Set[str],
        updates: Dict[str, Any],
        check_capacity: bool = False,
    ) -> Dict[str, Any]:
        async with self._lock:
            db = self.session_factory()
            try:
                job = db.query(InteractionJob).filter(InteractionJob.id == job_id).first()
                if not job:
                    raise InteractionJobNotFound(job_id)
                if job.status not in expected_statuses:
                    expected = ", ".join(sorted(expected_statuses))
                    raise InvalidJobTransition(f"Expected {expected}; found {job.status}")
                if check_capacity:
                    active_count = db.query(InteractionJob).filter(
                        InteractionJob.status.in_(ACTIVE_STATUSES)
                    ).count()
                    if active_count >= self.max_queue_size:
                        raise InteractionQueueError("queue_full")
                if job_id in self._enqueued_ids:
                    raise InvalidJobTransition("Job is already queued")
                job.status = "queued"
                for key, value in updates.items():
                    setattr(job, key, value)
                job.updated_at = datetime.utcnow()
                db.commit()
                db.refresh(job)
                payload = serialize_job(job)
                self._enqueued_ids.add(job_id)
                self.queue.put_nowait(job_id)
            finally:
                db.close()
        await self._notify(payload)
        return payload

    async def _cancel_current(self, reason: str) -> Optional[Dict[str, Any]]:
        async with self._attempt_lock:
            job_id = self.current_job_id
            if not job_id:
                return None
            current = self.get_job(job_id)
            if current["status"] in TERMINAL_STATUSES:
                return current
            if self.current_cancel_event:
                self.current_cancel_event.set()
            await self._send_stop(current)
            result = await self._force_terminal(job_id, "cancelled", reason)
            waiter = self.playback_waiters.get(job_id)
            if waiter:
                waiter.outcome = "cancelled"
                waiter.terminal_event.set()
            return result

    async def _send_stop(self, job: Dict[str, Any]) -> None:
        if not self.broadcast_callback or not job.get("playback_id"):
            return
        waiter = self.playback_waiters.get(job["id"])
        try:
            await self.broadcast_callback({
                "type": "tts_stop",
                "job_id": job["id"],
                "playback_id": job["playback_id"],
                "playback_owner": job["playback_owner"],
                "playback_renderer_id": waiter.renderer_id if waiter else "",
            })
        except Exception:
            logger.exception("Unable to stop playback for interaction job %s", job["id"])

    async def renderer_disconnected(self, source: str, renderer_id: str) -> None:
        async with self._attempt_lock:
            job_id = self.current_job_id
            waiter = self.playback_waiters.get(job_id) if job_id else None
            if not waiter or waiter.owner != source or waiter.renderer_id != renderer_id:
                return
            current = self.get_job(job_id)
            if current["status"] in TERMINAL_STATUSES:
                return
            result = await self._force_terminal(job_id, "error", "playback_renderer_disconnected")
            waiter.outcome = result["status"]
            waiter.terminal_event.set()

    async def _notify(self, job: Dict[str, Any]) -> None:
        if self.state_callback:
            try:
                await self.state_callback({"type": "interaction_job", "data": job})
            except Exception:
                logger.exception("Unable to broadcast interaction job %s", job.get("id", ""))
        await self._notify_queue()

    async def _notify_queue(self) -> None:
        if self.state_callback:
            try:
                await self.state_callback({"type": "interaction_queue", "data": self.status()})
            except Exception:
                logger.exception("Unable to broadcast interaction queue state")

    def _mark_interrupted_jobs(self) -> None:
        db = self.session_factory()
        try:
            jobs = db.query(InteractionJob).filter(InteractionJob.status.in_(ACTIVE_STATUSES)).all()
            if not jobs:
                return
            now = datetime.utcnow()
            for job in jobs:
                job.status = "error"
                job.error = "backend_restarted_before_completion"
                job.finished_at = now
                job.updated_at = now
            db.commit()
        finally:
            db.close()
