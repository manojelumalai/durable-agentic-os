"""Token-bucket rate limiter enforcing per-tenant requests and token budgets."""

import time


class TokenBucketRateLimiter:
    """Thread-safe in-memory token bucket rate limiter for API calls and LLM tokens."""

    def __init__(self, capacity: int, refill_rate_per_sec: float) -> None:
        self.capacity = float(capacity)
        self.tokens = float(capacity)
        self.refill_rate = float(refill_rate_per_sec)
        self.last_refill = time.monotonic()

    def consume(self, amount: int = 1) -> bool:
        """Attempt to consume tokens. Returns True if accepted, False if rate limited."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

        if self.tokens >= amount:
            self.tokens -= amount
            return True
        return False
