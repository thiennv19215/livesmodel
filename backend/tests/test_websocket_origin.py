import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from main import websocket_origin_allowed  # noqa: E402


class _WebSocket:
    def __init__(self, origin="", host="127.0.0.1:8000"):
        self.headers = {"host": host}
        if origin:
            self.headers["origin"] = origin


class WebSocketOriginTests(unittest.TestCase):
    def test_allows_same_host_and_configured_frontend(self):
        self.assertTrue(websocket_origin_allowed(_WebSocket("http://127.0.0.1:8000")))
        self.assertTrue(websocket_origin_allowed(_WebSocket("http://localhost:3000")))

    def test_rejects_cross_site_browser_origin(self):
        self.assertFalse(websocket_origin_allowed(_WebSocket("https://attacker.example")))

    def test_allows_renderer_without_browser_origin(self):
        self.assertTrue(websocket_origin_allowed(_WebSocket()))
