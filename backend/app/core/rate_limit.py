"""Rate limiting behind an interface so Redis can replace the in-memory backend later.

The in-memory implementation is per-process. It does not coordinate across multiple
API instances and is reset on restart. That is acceptable for this college-project
deployment; it is not production-internet hardening.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from typing import Protocol

from fastapi import Request

from app.core.config import get_settings
from app.core.errors import RateLimitedError


class RateLimiter(Protocol):
    def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        """Record one attempt. Return True if the attempt is allowed."""


class InMemoryRateLimiter:
    """Sliding-window counter stored in process memory."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            bucket = self._hits[key]
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                return False
            bucket.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


_limiter = InMemoryRateLimiter()


def get_rate_limiter() -> RateLimiter:
    return _limiter


def reset_rate_limiter() -> None:
    _limiter.reset()


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def rate_limit(scope: str, limit_attr: str, window_seconds: int = 60) -> Callable[..., None]:
    def dependency(request: Request) -> None:
        settings = get_settings()
        if not settings.rate_limit_enabled:
            return
        limit = int(getattr(settings, limit_attr))
        limiter = get_rate_limiter()
        key = f"{scope}:{client_ip(request)}"
        if not limiter.hit(key, limit, window_seconds):
            raise RateLimitedError("Too many requests. Try again shortly.")

    return dependency
