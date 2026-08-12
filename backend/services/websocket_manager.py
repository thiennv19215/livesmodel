import asyncio
import uuid
from typing import Any, Dict, Iterable

from fastapi import WebSocket


class ConnectionManager:
    """Owns WebSocket connection identity, serialized sends, and fan-out."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []
        self.connection_locks: Dict[WebSocket, asyncio.Lock] = {}
        self.connection_ids: Dict[WebSocket, str] = {}
        self.connections_by_id: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket) -> str:
        await websocket.accept()
        connection_id = str(uuid.uuid4())
        self.active_connections.append(websocket)
        self.connection_locks[websocket] = asyncio.Lock()
        self.connection_ids[websocket] = connection_id
        self.connections_by_id[connection_id] = websocket
        return connection_id

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        self.connection_locks.pop(websocket, None)
        connection_id = self.connection_ids.pop(websocket, "")
        if connection_id:
            self.connections_by_id.pop(connection_id, None)

    async def _send(self, connection: WebSocket, message: Dict[str, Any]) -> bool:
        lock = self.connection_locks.get(connection)
        if lock is None:
            return False
        try:
            async with lock:
                await asyncio.wait_for(connection.send_json(message), timeout=2.0)
            return True
        except Exception:
            self.disconnect(connection)
            return False

    async def broadcast(self, message: Dict[str, Any]) -> None:
        connections = list(self.active_connections)
        if connections:
            await asyncio.gather(*(self._send(connection, message) for connection in connections))

    async def send_to(self, connection_id: str, message: Dict[str, Any]) -> bool:
        connection = self.connections_by_id.get(connection_id)
        if not connection:
            return False
        return await self._send(connection, message)

    @property
    def connection_count(self) -> int:
        return len(self.active_connections)

    @property
    def first_connection_id(self) -> str:
        if not self.active_connections:
            return ""
        return self.connection_ids.get(self.active_connections[0], "")


def normalize_origins(cors_origins: str) -> set[str]:
    return {
        origin.strip().rstrip("/")
        for origin in cors_origins.split(",")
        if origin.strip()
    }


def websocket_origin_allowed(websocket: WebSocket, allowed_origins: Iterable[str]) -> bool:
    """Reject cross-site browser WebSockets while allowing non-browser renderers."""
    origin = (websocket.headers.get("origin") or "").rstrip("/")
    if not origin:
        return True
    host = websocket.headers.get("host") or ""
    same_host_origins = {f"http://{host}", f"https://{host}"} if host else set()
    return origin in set(allowed_origins) or origin in same_host_origins
