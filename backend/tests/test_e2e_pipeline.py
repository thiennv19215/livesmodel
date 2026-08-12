import time
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

import main


class InteractionPipelineE2ETests(unittest.TestCase):
    def setUp(self):
        self.original_playback_timeout = main.interaction_queue.playback_timeout_seconds
        self.original_playback_start_timeout = main.interaction_queue.playback_start_timeout_seconds
        main.interaction_queue.playback_timeout_seconds = 1.0
        main.interaction_queue.playback_start_timeout_seconds = 0.5

    def tearDown(self):
        main.interaction_queue.playback_timeout_seconds = self.original_playback_timeout
        main.interaction_queue.playback_start_timeout_seconds = self.original_playback_start_timeout

    def _wait_for_job(self, client: TestClient, job_id: str, expected_status: str, timeout: float = 2.0):
        deadline = time.monotonic() + timeout
        last = None
        while time.monotonic() < deadline:
            response = client.get(f"/api/interaction-jobs/{job_id}")
            self.assertEqual(response.status_code, 200)
            last = response.json()
            if last["status"] == expected_status:
                return last
            time.sleep(0.01)
        self.fail(f"Timed out waiting for {job_id} -> {expected_status}; last={last}")

    def test_manual_event_runs_through_tts_renderer_ack_to_done(self):
        fake_audio = "/static/audio/e2e.mp3"
        with patch.object(main.tts_service, "generate_speech", new=AsyncMock(return_value=fake_audio)):
            with TestClient(main.app) as client:
                with client.websocket_connect("/ws/scene") as scene:
                    hello = scene.receive_json()
                    self.assertEqual(hello["type"], "renderer_hello")
                    self.assertEqual(hello["renderer_type"], "scene")

                    response = client.post(
                        "/api/manual_event",
                        json={"user_name": "E2E Tester", "event_type": "member"},
                    )
                    self.assertEqual(response.status_code, 200)
                    job = response.json()["job"]
                    job_id = job["id"]

                    play = scene.receive_json()
                    self.assertEqual(play["type"], "tts_play")
                    self.assertEqual(play["job_id"], job_id)
                    self.assertEqual(play["audio_url"], fake_audio)

                    scene.send_json({
                        "type": "playback_ack",
                        "job_id": job_id,
                        "playback_id": play["playback_id"],
                        "state": "started",
                    })
                    started_ack = scene.receive_json()
                    self.assertEqual(started_ack["type"], "playback_ack_accepted")
                    self.assertEqual(started_ack["data"]["status"], "playing")

                    scene.send_json({
                        "type": "playback_ack",
                        "job_id": job_id,
                        "playback_id": play["playback_id"],
                        "state": "ended",
                    })
                    ended_ack = scene.receive_json()
                    self.assertEqual(ended_ack["type"], "playback_ack_accepted")
                    self.assertEqual(ended_ack["data"]["status"], "done")

                    final_job = self._wait_for_job(client, job_id, "done")
                    self.assertEqual(final_job["playback_owner"], "scene")
                    self.assertTrue(final_job["finished_at"])

    def test_renderer_disconnect_fails_current_job_and_releases_queue(self):
        fake_audio = "/static/audio/e2e-disconnect.mp3"
        with patch.object(main.tts_service, "generate_speech", new=AsyncMock(return_value=fake_audio)):
            with TestClient(main.app) as client:
                with client.websocket_connect("/ws/scene") as scene:
                    scene.receive_json()
                    response = client.post(
                        "/api/manual_event",
                        json={"user_name": "Disconnect Tester", "event_type": "member"},
                    )
                    self.assertEqual(response.status_code, 200)
                    job_id = response.json()["job"]["id"]
                    play = scene.receive_json()
                    self.assertEqual(play["type"], "tts_play")
                    self.assertEqual(play["job_id"], job_id)

                failed = self._wait_for_job(client, job_id, "error")
                self.assertEqual(failed["error"], "playback_renderer_disconnected")

                queue = client.get("/api/interaction-queue")
                self.assertEqual(queue.status_code, 200)
                deadline = time.monotonic() + 2.0
                state = queue.json()
                while state["current_job_id"] and time.monotonic() < deadline:
                    time.sleep(0.01)
                    state = client.get("/api/interaction-queue").json()
                self.assertEqual(state["current_job_id"], "")


if __name__ == "__main__":
    unittest.main()
