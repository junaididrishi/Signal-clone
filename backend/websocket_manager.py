import asyncio
import json
import os
from typing import Dict, Set

import redis.asyncio as aioredis
from fastapi import WebSocket

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

_redis: aioredis.Redis | None = None


async def init_redis():
    global _redis
    _redis = aioredis.from_url(REDIS_URL, decode_responses=True)


async def close_redis():
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None


def _channel(user_id: int) -> str:
    return f"chat:user:{user_id}"


class ConnectionManager:
    def __init__(self):
        # user_id -> set of local websockets on THIS process
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # user_id -> asyncio Task (listener)
        self._listener_tasks: Dict[int, asyncio.Task] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
            self._listener_tasks[user_id] = asyncio.create_task(
                self._subscribe(user_id)
            )
        self.active_connections[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                task = self._listener_tasks.pop(user_id, None)
                if task:
                    task.cancel()

    async def send_to_user(self, user_id: int, data: dict):
        """Publish to Redis — any server instance with that user connected will deliver it."""
        if _redis:
            await _redis.publish(_channel(user_id), json.dumps(data))
        else:
            # fallback: in-process delivery (dev without Redis)
            await self._deliver_local(user_id, data)

    async def broadcast_to_conversation(
        self, conversation_id: int, data: dict, participant_ids: list
    ):
        for user_id in participant_ids:
            await self.send_to_user(user_id, data)

    def is_online(self, user_id: int) -> bool:
        return bool(self.active_connections.get(user_id))

    async def _subscribe(self, user_id: int):
        """Background task: subscribe to Redis channel and forward to local WS connections."""
        if not _redis:
            return
        pubsub = _redis.pubsub()
        await pubsub.subscribe(_channel(user_id))
        try:
            async for raw in pubsub.listen():
                if raw["type"] != "message":
                    continue
                try:
                    data = json.loads(raw["data"])
                except (json.JSONDecodeError, TypeError):
                    continue
                await self._deliver_local(user_id, data)
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(_channel(user_id))
            await pubsub.aclose()

    async def _deliver_local(self, user_id: int, data: dict):
        """Send to every WebSocket on this process for this user."""
        sockets = self.active_connections.get(user_id)
        if not sockets:
            return
        dead: Set[WebSocket] = set()
        payload = json.dumps(data)
        for ws in list(sockets):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)
        for ws in dead:
            sockets.discard(ws)


manager = ConnectionManager()
