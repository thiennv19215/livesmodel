import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from main import ConnectionManager  # noqa: E402


class FakeWebSocket:
    def __init__(self):
        self.accepted = False
        self.messages = []

    async def accept(self):
        self.accepted = True

    async def send_json(self, message):
        self.messages.append(message)


class ConnectionManagerTests(unittest.IsolatedAsyncioTestCase):
    async def test_targeted_send_reaches_only_the_leased_renderer(self):
        manager = ConnectionManager()
        first = FakeWebSocket()
        second = FakeWebSocket()
        first_id = await manager.connect(first)
        await manager.connect(second)

        delivered = await manager.send_to(first_id, {"type": "tts_play"})

        self.assertTrue(delivered)
        self.assertEqual(first.messages, [{"type": "tts_play"}])
        self.assertEqual(second.messages, [])
        self.assertEqual(manager.first_connection_id, first_id)

    async def test_broadcast_still_reaches_all_observers(self):
        manager = ConnectionManager()
        first = FakeWebSocket()
        second = FakeWebSocket()
        await manager.connect(first)
        await manager.connect(second)

        await manager.broadcast({"type": "interaction_job"})

        self.assertEqual(first.messages, [{"type": "interaction_job"}])
        self.assertEqual(second.messages, [{"type": "interaction_job"}])


if __name__ == "__main__":
    unittest.main()
