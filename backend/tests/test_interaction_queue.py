import asyncio
import sys
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import Base  # noqa: E402
from services.interaction_queue import (  # noqa: E402
    InteractionJobNotFound,
    InteractionQueueError,
    InteractionQueueService,
    InvalidJobTransition,
)


class FakeTTSService:
    async def generate_speech(self, text: str):
        await asyncio.sleep(0)
        return f"/static/audio/{text}.mp3"


class CancelAwareTTSService:
    def __init__(self):
        self.calls = 0
        self.first_cancelled = asyncio.Event()

    async def generate_speech(self, text: str):
        self.calls += 1
        if self.calls == 1:
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                self.first_cancelled.set()
                raise
        return f"/static/audio/{text}.mp3"


class InteractionQueueTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine)
        self.commands = []
        self.updates = []
        self.renderer_id = "live-renderer-1"
        self.service = InteractionQueueService(
            session_factory=self.Session,
            tts_service=FakeTTSService(),
            max_queue_size=100,
            tts_timeout_seconds=1,
            playback_timeout_seconds=1,
        )

        async def broadcast(command):
            self.commands.append(command)

        async def state_update(update):
            self.updates.append(update)

        await self.service.start(
            broadcast,
            state_update,
            lambda: ("live", self.renderer_id),
        )

    async def asyncTearDown(self):
        await self.service.stop()

    async def wait_for(self, predicate, timeout=1.0):
        deadline = asyncio.get_running_loop().time() + timeout
        while asyncio.get_running_loop().time() < deadline:
            if predicate():
                return
            await asyncio.sleep(0.005)
        self.fail("Timed out waiting for queue state")

    async def enqueue_job(self, message="xin chao"):
        job = await self.service.create_job("chat", "user-1", "Tester", message)
        await self.service.mark_ai_processing(job["id"])
        return await self.service.set_ai_reply_and_enqueue(job["id"], message)

    async def test_job_waits_for_real_playback_ack(self):
        job = await self.enqueue_job()
        await self.wait_for(lambda: len(self.commands) == 1)

        command = self.commands[0]
        self.assertEqual(self.service.get_job(job["id"])["status"], "ready")
        await self.service.acknowledge_playback(
            job["id"], command["playback_id"], "started", "live",
            renderer_id=self.renderer_id,
        )
        self.assertEqual(self.service.get_job(job["id"])["status"], "playing")

        await self.service.acknowledge_playback(
            job["id"], command["playback_id"], "ended", "live",
            renderer_id=self.renderer_id,
        )
        await self.wait_for(lambda: self.service.status()["current_job_id"] == "")
        self.assertEqual(self.service.get_job(job["id"])["status"], "done")

    async def test_failed_playback_releases_next_job(self):
        first = await self.enqueue_job("first")
        second = await self.enqueue_job("second")
        await self.wait_for(lambda: len(self.commands) == 1)

        first_command = self.commands[0]
        await self.service.acknowledge_playback(
            first["id"], first_command["playback_id"], "failed", "live", "decoder_error",
            renderer_id=self.renderer_id,
        )
        await self.wait_for(lambda: len(self.commands) == 2)
        self.assertEqual(self.service.get_job(first["id"])["status"], "error")
        self.assertEqual(self.commands[1]["job_id"], second["id"])

        second_command = self.commands[1]
        await self.service.acknowledge_playback(
            second["id"], second_command["playback_id"], "started", "live",
            renderer_id=self.renderer_id,
        )
        await self.service.acknowledge_playback(
            second["id"], second_command["playback_id"], "ended", "live",
            renderer_id=self.renderer_id,
        )

    async def test_stale_playback_id_is_rejected(self):
        job = await self.enqueue_job()
        await self.wait_for(lambda: len(self.commands) == 1)
        with self.assertRaises(InteractionQueueError):
            await self.service.acknowledge_playback(
                job["id"], "00000000-0000-0000-0000-000000000000", "ended", "live",
                renderer_id=self.renderer_id,
            )

    async def test_clear_cancels_pending_and_current_jobs(self):
        first = await self.enqueue_job("first")
        second = await self.enqueue_job("second")
        await self.wait_for(lambda: len(self.commands) == 1)
        result = await self.service.clear(include_current=True)
        await self.wait_for(lambda: self.service.status()["current_job_id"] == "")

        self.assertIn(first["id"], result["cancelled_job_ids"])
        self.assertIn(second["id"], result["cancelled_job_ids"])
        self.assertEqual(self.service.get_job(first["id"])["status"], "cancelled")
        self.assertEqual(self.service.get_job(second["id"])["status"], "cancelled")

    async def test_skip_sends_stop_before_next_playback(self):
        first = await self.enqueue_job("first")
        second = await self.enqueue_job("second")
        await self.wait_for(lambda: len(self.commands) == 1)

        await self.service.skip_current()
        await self.wait_for(lambda: len([c for c in self.commands if c["type"] == "tts_play"]) == 2)

        self.assertEqual(
            [command["type"] for command in self.commands[:3]],
            ["tts_play", "tts_stop", "tts_play"],
        )
        self.assertEqual(self.commands[1]["job_id"], first["id"])
        self.assertEqual(self.commands[2]["job_id"], second["id"])

        second_command = self.commands[2]
        await self.service.acknowledge_playback(
            second["id"], second_command["playback_id"], "started", "live",
            renderer_id=self.renderer_id,
        )
        await self.service.acknowledge_playback(
            second["id"], second_command["playback_id"], "ended", "live",
            renderer_id=self.renderer_id,
        )

    async def test_playback_timeout_stops_audio_and_releases_next_job(self):
        self.service.playback_timeout_seconds = 0.05
        first = await self.enqueue_job("timeout-first")
        second = await self.enqueue_job("timeout-second")

        await self.wait_for(
            lambda: len([c for c in self.commands if c["type"] == "tts_play"]) == 2,
        )
        self.assertEqual(self.service.get_job(first["id"])["status"], "error")
        self.assertEqual(self.service.get_job(first["id"])["error"], "playback_ack_timeout")
        self.assertEqual(
            [command["type"] for command in self.commands[:3]],
            ["tts_play", "tts_stop", "tts_play"],
        )

        second_command = [
            command for command in self.commands
            if command["type"] == "tts_play" and command["job_id"] == second["id"]
        ][0]
        await self.service.acknowledge_playback(
            second["id"], second_command["playback_id"], "failed", "live", "test_cleanup",
            renderer_id=self.renderer_id,
        )

    async def test_duplicate_terminal_ack_is_idempotent(self):
        job = await self.enqueue_job("duplicate")
        await self.wait_for(lambda: len(self.commands) == 1)
        command = self.commands[0]
        await self.service.acknowledge_playback(
            job["id"], command["playback_id"], "started", "live",
            renderer_id=self.renderer_id,
        )
        await self.service.acknowledge_playback(
            job["id"], command["playback_id"], "ended", "live",
            renderer_id=self.renderer_id,
        )
        await self.wait_for(lambda: self.service.status()["current_job_id"] == "")

        duplicate = await self.service.acknowledge_playback(
            job["id"], command["playback_id"], "ended", "live",
            renderer_id=self.renderer_id,
        )
        self.assertEqual(duplicate["status"], "done")

    async def test_ack_rejects_non_owner_renderer_and_end_before_start(self):
        job = await self.enqueue_job("owner")
        await self.wait_for(lambda: len(self.commands) == 1)
        command = self.commands[0]

        with self.assertRaises(InteractionQueueError):
            await self.service.acknowledge_playback(
                job["id"], command["playback_id"], "started", "live",
                renderer_id="different-renderer",
            )
        with self.assertRaises(InvalidJobTransition):
            await self.service.acknowledge_playback(
                job["id"], command["playback_id"], "ended", "live",
                renderer_id=self.renderer_id,
            )

    async def test_ack_for_unknown_job_is_not_found(self):
        with self.assertRaises(InteractionJobNotFound):
            await self.service.acknowledge_playback(
                "missing-job",
                "00000000-0000-0000-0000-000000000000",
                "started",
                "live",
                renderer_id=self.renderer_id,
            )

    async def test_cancel_pending_releases_logical_capacity(self):
        first = await self.enqueue_job("active")
        second = await self.enqueue_job("pending")
        await self.wait_for(lambda: len(self.commands) == 1)
        self.assertEqual(self.service.status()["pending_count"], 1)

        await self.service.cancel(second["id"])
        self.assertEqual(self.service.status()["pending_count"], 0)
        first_command = self.commands[0]
        await self.service.acknowledge_playback(
            first["id"], first_command["playback_id"], "failed", "live", "test_cleanup",
            renderer_id=self.renderer_id,
        )

    async def test_retry_creates_new_playback_lease(self):
        job = await self.enqueue_job("retry")
        await self.wait_for(lambda: len(self.commands) == 1)
        first_command = self.commands[0]
        await self.service.acknowledge_playback(
            job["id"], first_command["playback_id"], "failed", "live", "decoder_error",
            renderer_id=self.renderer_id,
        )
        await self.wait_for(lambda: self.service.status()["current_job_id"] == "")

        retried = await self.service.retry(job["id"])
        self.assertEqual(retried["retry_count"], 1)
        await self.wait_for(lambda: len(self.commands) == 2)
        second_command = self.commands[1]
        self.assertNotEqual(first_command["playback_id"], second_command["playback_id"])
        await self.service.acknowledge_playback(
            job["id"], second_command["playback_id"], "failed", "live", "test_cleanup",
            renderer_id=self.renderer_id,
        )

    async def test_capacity_skips_job_after_limit(self):
        self.service.max_queue_size = 2
        first = await self.service.create_job("chat", "u1", "One", "one")
        second = await self.service.create_job("chat", "u2", "Two", "two")
        third = await self.service.create_job("chat", "u3", "Three", "three")
        self.assertEqual(first["status"], "received")
        self.assertEqual(second["status"], "received")
        self.assertEqual(third["status"], "skipped")
        self.assertEqual(third["decision_reason"], "queue_full")

    async def test_skip_cancels_inflight_tts_generation(self):
        cancel_aware_tts = CancelAwareTTSService()
        self.service.tts_service = cancel_aware_tts
        first = await self.enqueue_job("slow-first")
        second = await self.enqueue_job("fast-second")
        await self.wait_for(
            lambda: self.service.get_job(first["id"])["status"] == "tts_processing",
        )

        await self.service.skip_current()
        await self.wait_for(lambda: cancel_aware_tts.first_cancelled.is_set())
        await self.wait_for(lambda: len(self.commands) == 1)
        self.assertEqual(self.commands[0]["job_id"], second["id"])
        self.assertEqual(self.service.get_job(first["id"])["status"], "cancelled")

        await self.service.acknowledge_playback(
            second["id"], self.commands[0]["playback_id"], "failed", "live", "test_cleanup",
            renderer_id=self.renderer_id,
        )

    async def test_owner_disconnect_releases_next_job(self):
        first = await self.enqueue_job("disconnect-first")
        second = await self.enqueue_job("disconnect-second")
        await self.wait_for(lambda: len(self.commands) == 1)

        await self.service.renderer_disconnected("live", self.renderer_id)
        await self.wait_for(lambda: len(self.commands) == 2)
        self.assertEqual(self.service.get_job(first["id"])["status"], "error")
        self.assertEqual(
            self.service.get_job(first["id"])["error"],
            "playback_renderer_disconnected",
        )
        self.assertEqual(self.commands[1]["job_id"], second["id"])

        await self.service.acknowledge_playback(
            second["id"], self.commands[1]["playback_id"], "failed", "live", "test_cleanup",
            renderer_id=self.renderer_id,
        )


if __name__ == "__main__":
    unittest.main()
