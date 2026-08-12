import asyncio
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, Tuple, Union

from sqlalchemy.orm import Session

try:
    from database import InteractionJob
except ModuleNotFoundError:
    from backend.database import InteractionJob

from .interaction_queue_legacy import (
    ACTIVE_STATUSES,
    ALLOWED_TRANSITIONS,
    TERMINAL_STATUSES,
    InteractionJobNotFound,
    InteractionQueueError,
    InvalidJobTransition,
    InteractionQueueService as LegacyInteractionQueueService,
    PlaybackWaiter,
    serialize_job,
)


RECOVERABLE_AFTER_RESTART = {"queued", "ready"}


class InteractionQueueService(LegacyInteractionQueueService):
    """Reliability layer for restart recovery and playback-start deadlines."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        tts_service: Any,
        max_queue_size: int = 100,
        tts_timeout_seconds: float = 120.0,
        playback_timeout_seconds: float = 120.0,
        playback_start_timeout_seconds: float = 15.0,
    ) -> None:
        self.playback_start_timeout_seconds = playback_start_timeout_seconds
        self._playback_start_watchdogs: Dict[str, asyncio.Task] = {}
        super().__init__(
            session_factory=session_factory,
            tts_service=tts_service,
            max_queue_size=max_queue_size,
            tts_timeout_seconds=tts_timeout_seconds,
            playback_timeout_seconds=playback_timeout_seconds + playback_start_timeout_seconds,
        )

    async def start(
        self,
        broadcast_callback: Callable[[Dict[str, Any]], Awaitable[None]],
        state_callback: Callable[[Dict[str, Any]], Awaitable[None]],
        owner_selector: Callable[[], Union[str, Tuple[str, str]]],
    ) -> None:
        async def guarded_broadcast(message: Dict[str, Any]) -> None:
            if message.get("type") == "tts_play":
                self._arm_playback_start_watchdog(
                    message.get("job_id", ""),
                    message.get("playback_id", ""),
                )
            await broadcast_callback(message)

        await super().start(guarded_broadcast, state_callback, owner_selector)

    async def stop(self) -> None:
        for task in list(self._playback_start_watchdogs.values()):
            task.cancel()
        self._playback_start_watchdogs.clear()
        await super().stop()

    async def acknowledge_playback(
        self,
        job_id: str,
        playback_id: str,
        state: str,
        source: str,
        error: str = "",
        renderer_id: str = "",
    ) -> Dict[str, Any]:
        result = await super().acknowledge_playback(
            job_id=job_id,
            playback_id=playback_id,
            state=state,
            source=source,
            error=error,
            renderer_id=renderer_id,
        )
        if state in {"started", "ended", "failed"}:
            self._cancel_playback_start_watchdog(job_id)
        return result

    def _arm_playback_start_watchdog(self, job_id: str, playback_id: str) -> None:
        if not job_id or not playback_id or self.playback_start_timeout_seconds <= 0:
            return
        self._cancel_playback_start_watchdog(job_id)
        self._playback_start_watchdogs[job_id] = asyncio.create_task(
            self._watch_playback_start(job_id, playback_id),
            name=f"playback-start-watchdog-{job_id}",
        )

    def _cancel_playback_start_watchdog(self, job_id: str) -> None:
        task = self._playback_start_watchdogs.pop(job_id, None)
        if task and task is not asyncio.current_task() and not task.done():
            task.cancel()

    async def _watch_playback_start(self, job_id: str, playback_id: str) -> None:
        try:
            await asyncio.sleep(self.playback_start_timeout_seconds)
            async with self._attempt_lock:
                current = self.get_job(job_id)
                if current["status"] != "ready" or current["playback_id"] != playback_id:
                    return
                await self._send_stop(current)
                result = await self._force_terminal(job_id, "error", "playback_start_timeout")
                waiter = self.playback_waiters.get(job_id)
                if waiter:
                    waiter.outcome = result["status"]
                    waiter.terminal_event.set()
        except asyncio.CancelledError:
            raise
        finally:
            self._playback_start_watchdogs.pop(job_id, None)

    def _mark_interrupted_jobs(self) -> None:
        """Recover safe queued work; never resume an in-flight playback."""
        db = self.session_factory()
        recovered_ids = []
        try:
            jobs = db.query(InteractionJob).filter(InteractionJob.status.in_(ACTIVE_STATUSES)).all()
            if not jobs:
                return
            now = datetime.utcnow()
            for job in jobs:
                previous_status = job.status
                if previous_status in RECOVERABLE_AFTER_RESTART and (job.ai_reply or "").strip():
                    job.status = "queued"
                    job.error = ""
                    job.decision_reason = "recovered_after_restart"
                    job.audio_url = ""
                    job.playback_id = ""
                    job.playback_owner = ""
                    job.started_at = None
                    job.finished_at = None
                    job.updated_at = now
                    recovered_ids.append(job.id)
                    continue

                job.status = "error"
                job.error = (
                    "playback_interrupted"
                    if previous_status == "playing"
                    else "backend_restarted_before_completion"
                )
                job.finished_at = now
                job.updated_at = now
            db.commit()
        finally:
            db.close()

        for job_id in recovered_ids:
            if job_id not in self._enqueued_ids:
                self._enqueued_ids.add(job_id)
                self.queue.put_nowait(job_id)


__all__ = [
    "ACTIVE_STATUSES",
    "ALLOWED_TRANSITIONS",
    "TERMINAL_STATUSES",
    "InteractionJobNotFound",
    "InteractionQueueError",
    "InteractionQueueService",
    "InvalidJobTransition",
    "PlaybackWaiter",
    "serialize_job",
]
