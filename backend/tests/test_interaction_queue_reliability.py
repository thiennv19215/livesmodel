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

from database import Base, InteractionJob  # noqa: E402
from services.interaction_queue import InteractionQueueService  # noqa: E402


class FakeTTSService:
    async def generate_speech(self, text: str):
        await asyncio.sleep(0)
        return f"/static/audio/{text}.mp3"


class ReliabilityTests(unittest.IsolatedAsyncioTestCase):
    def make_session(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        return sessionmaker(bind=engine)

    async def wait_for(self, predicate, timeout=1.0):
        deadline = asyncio.get_running_loop().time() + timeout
        while asyncio.get_running_loop().time() < deadline:
            if predicate():
                return
            await asyncio.sleep(0.005)
        self.fail("Timed out waiting for reliability state")

    async def test_restart_recovers_queued_and_ready_but_interrupts_playing(self):
        Session = self.make_session()
        db = Session()
        try:
            db.add_all([
                InteractionJob(id="queued", event_type="chat", status="queued", ai_reply="one"),
                InteractionJob(id="ready", event_type="chat", status="ready", ai_reply="two", playback_id="old"),
                InteractionJob(id="playing", event_type="chat", status="playing", ai_reply="three", playback_id="live"),
                InteractionJob(id="ai", event_type="chat", status="ai_processing", ai_reply=""),
            ])
            db.commit()
        finally:
            db.close()

        service = InteractionQueueService(Session, FakeTTSService())
        service._mark_interrupted_jobs()

        self.assertEqual(service.get_job("queued")["status"], "queued")
        self.assertEqual(service.get_job("ready")["status"], "queued")
        self.assertEqual(service.get_job("ready")["playback_id"], "")
        self.assertEqual(service.get_job("playing")["status"], "error")
        self.assertEqual(service.get_job("playing")["error"], "playback_interrupted")
        self.assertEqual(service.get_job("ai")["status"], "error")
        self.assertEqual(service.status()["pending_count"], 2)

    async def test_renderer_must_ack_started_before_start_deadline(self):
        Session = self.make_session()
        commands = []
        service = InteractionQueueService(
            Session,
            FakeTTSService(),
            tts_timeout_seconds=1,
            playback_timeout_seconds=1,
            playback_start_timeout_seconds=0.05,
        )

        async def broadcast(command):
            commands.append(command)

        async def state_update(_update):
            return None

        await service.start(broadcast, state_update, lambda: ("live", "renderer-1"))
        try:
            job = await service.create_job("chat", "u1", "Tester", "hello")
            await service.mark_ai_processing(job["id"])
            await service.set_ai_reply_and_enqueue(job["id"], "hello")

            await self.wait_for(
                lambda: service.get_job(job["id"])["status"] == "error",
                timeout=0.5,
            )
            failed = service.get_job(job["id"])
            self.assertEqual(failed["error"], "playback_start_timeout")
            self.assertEqual(
                [command["type"] for command in commands[:2]],
                ["tts_play", "tts_stop"],
            )
        finally:
            await service.stop()


if __name__ == "__main__":
    unittest.main()
