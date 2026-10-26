from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque


def _shared_auth() -> bool:
    return os.getenv("SENTRIX_SHARED_AUTH", "0") == "1"


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _allow_shared(self, key: str) -> bool:
        from sqlalchemy import text

        from .db import get_engine

        window_start = int(time.time() // self.window_seconds) * self.window_seconds
        with get_engine().begin() as connection:
            row = connection.execute(
                text(
                    """
                    SELECT hits FROM rate_limit_bucket
                    WHERE bucket_key = :key AND window_start = :window
                    FOR UPDATE
                    """
                ),
                {"key": key, "window": window_start},
            ).first()
            if row is None:
                connection.execute(
                    text(
                        """
                        INSERT INTO rate_limit_bucket (bucket_key, window_start, hits)
                        VALUES (:key, :window, 1)
                        ON CONFLICT (bucket_key, window_start) DO UPDATE
                        SET hits = rate_limit_bucket.hits + 1
                        """
                    ),
                    {"key": key, "window": window_start},
                )
                return True
            if row[0] >= self.limit:
                return False
            connection.execute(
                text(
                    """
                    UPDATE rate_limit_bucket
                    SET hits = hits + 1
                    WHERE bucket_key = :key AND window_start = :window
                    """
                ),
                {"key": key, "window": window_start},
            )
            return True

    def allow(self, key: str) -> bool:
        if _shared_auth():
            try:
                return self._allow_shared(key)
            except Exception:
                # Fail back to the local limiter if the shared store is down.
                pass
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.limit:
                return False
            events.append(now)
            return True
