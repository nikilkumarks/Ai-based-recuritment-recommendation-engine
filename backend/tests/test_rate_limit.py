from app.core.rate_limit import InMemoryRateLimiter


def test_in_memory_rate_limiter_blocks_after_limit() -> None:
    limiter = InMemoryRateLimiter()
    assert limiter.hit("login:1.1.1.1", limit=3, window_seconds=60)
    assert limiter.hit("login:1.1.1.1", limit=3, window_seconds=60)
    assert limiter.hit("login:1.1.1.1", limit=3, window_seconds=60)
    assert limiter.hit("login:1.1.1.1", limit=3, window_seconds=60) is False
    assert limiter.hit("login:2.2.2.2", limit=3, window_seconds=60)


def test_in_memory_rate_limiter_reset() -> None:
    limiter = InMemoryRateLimiter()
    limiter.hit("k", 1, 60)
    assert limiter.hit("k", 1, 60) is False
    limiter.reset()
    assert limiter.hit("k", 1, 60)
