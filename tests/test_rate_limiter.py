"""Unit tests for TokenBucketRateLimiter."""

import time

from durable_agent.safeguards.rate_limiter import TokenBucketRateLimiter


def test_rate_limiter_consumes_available_tokens() -> None:
    limiter = TokenBucketRateLimiter(capacity=5, refill_rate_per_sec=10.0)

    # Consume 3 tokens
    assert limiter.consume(3) is True
    # Consume 2 tokens
    assert limiter.consume(2) is True
    # Capacity exhausted
    assert limiter.consume(1) is False


def test_rate_limiter_refills_over_time() -> None:
    limiter = TokenBucketRateLimiter(capacity=2, refill_rate_per_sec=20.0)
    assert limiter.consume(2) is True
    assert limiter.consume(1) is False

    time.sleep(0.12)  # Should refill ~2.4 tokens -> capped at 2
    assert limiter.consume(1) is True
