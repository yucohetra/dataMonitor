import asyncio
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings
from app.services.record_service import RecordService


@dataclass
class FlushStats:
    last_flush_time: datetime | None = None
    last_flush_count: int = 0
    last_flush_success: bool = True


class RealtimeBuffer:
    """
    Thread-safe buffer for batching realtime events.

    Design considerations:
    - Uses an asyncio Lock to protect concurrent access in async runtime.
    - Applies an upper bound to reduce memory risk under DB outages.
    """

    def __init__(self, max_size: int):
        self._items: list[dict[str, Any]] = []
        self._lock = asyncio.Lock()
        self._max_size = max_size

    async def add(self, item: dict[str, Any]) -> None:
        async with self._lock:
            if len(self._items) >= self._max_size:
                # NOTE:
                # - Drop strategy is used to prevent unbounded memory growth.
                # - For production, consider persisting to a durable queue.
                self._items.pop(0)
            self._items.append(item)

    async def drain(self) -> list[dict[str, Any]]:
        async with self._lock:
            batch = self._items
            self._items = []
            return batch

    async def size(self) -> int:
        async with self._lock:
            return len(self._items)


class WebSocketBroadcaster:
    """
    Manages WS connections and broadcasts realtime events.

    Design considerations:
    - Maintains a set of active connections for server-side broadcast.
    - Removes dead connections to avoid backpressure.
    """

    def __init__(self):
        self._connections = set()
        self._lock = asyncio.Lock()

    async def add(self, websocket) -> None:
        async with self._lock:
            self._connections.add(websocket)

    async def remove(self, websocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def count(self) -> int:
        async with self._lock:
            return len(self._connections)

    async def broadcast(self, payload: dict) -> None:
        async with self._lock:
            conns = list(self._connections)

        dead = []
        for ws in conns:
            try:
                await ws.send_json({"event": "realtime_data", "data": payload})
            except Exception:
                dead.append(ws)

        for ws in dead:
            await self.remove(ws)


class RealtimeGenerator:
    """
    Generates realtime events at a fixed interval.

    Design considerations:
    - Generates deterministic schema for WS + DB persistence.
    - Centralizes anomaly flag calculation for consistency.
    """

    def __init__(self, buffer: RealtimeBuffer):
        self._buffer = buffer
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    async def run(self, broadcaster: WebSocketBroadcaster) -> None:
        self._running = True
        categories = ["A", "B", "C"]
        while self._running:
            value = round(random.uniform(0, 120), 2)
            cat = random.choice(categories)
            ts = datetime.now(timezone.utc)

            payload = {
                "title": "realtime_sensor",
                "value": value,
                "category": cat,
                "timestamp": ts.isoformat(),
                "is_anomaly": RecordService.is_anomaly(value),
                "source": "generator",
            }

            # NOTE:
            # - Same event is sent to WS and buffered for batch persistence.
            await broadcaster.broadcast(payload)
            await self._buffer.add(payload)

            await asyncio.sleep(int(settings.GENERATOR_INTERVAL_SECONDS))

    def stop(self) -> None:
        self._running = False
