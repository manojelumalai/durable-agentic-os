"""Multi-provider LLM gateway with circuit breaker failover across OpenAI, Anthropic, and Gemini."""

import asyncio
import logging
import time
from enum import Enum
from typing import Any

from durable_agent.llm.semantic_cache import TwoTierSemanticCache

logger = logging.getLogger(__name__)


class Provider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Fail-safe breaker tracking failure rates per provider."""

    def __init__(self, failure_threshold: int = 3, reset_timeout_sec: float = 30.0) -> None:
        self.failure_threshold = failure_threshold
        self.reset_timeout_sec = reset_timeout_sec
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = CircuitState.CLOSED

    def record_success(self) -> None:
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.monotonic()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

    def allow_request(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        now = time.monotonic()
        if self.state == CircuitState.OPEN and now - self.last_failure_time > self.reset_timeout_sec:
            self.state = CircuitState.HALF_OPEN
            return True
        return self.state == CircuitState.HALF_OPEN


class MultiProviderLLMGateway:
    """Intelligent router routing inference requests with semantic caching and automatic failover."""

    def __init__(self, cache: TwoTierSemanticCache | None = None) -> None:
        self.cache = cache or TwoTierSemanticCache()
        self.breakers = {
            Provider.OPENAI: CircuitBreaker(),
            Provider.ANTHROPIC: CircuitBreaker(),
            Provider.GEMINI: CircuitBreaker(),
        }
        self.provider_priority = [Provider.OPENAI, Provider.ANTHROPIC, Provider.GEMINI]

    async def complete(self, prompt: str, system_prompt: str | None = None) -> dict[str, Any]:
        """Generate response with cache check and resilient fallback across providers."""
        # Check Two-Tier Cache first
        cached_val, hit_type = self.cache.get(prompt)
        if cached_val is not None:
            return {
                "content": cached_val,
                "provider": "cache",
                "cache_hit": hit_type,
            }

        # Route through active healthy providers
        for provider in self.provider_priority:
            breaker = self.breakers[provider]
            if not breaker.allow_request():
                logger.warning(f"Circuit open for provider {provider.value}; falling back to next provider")
                continue

            try:
                # Simulated upstream response generation
                result = await self._simulate_provider_call(provider, prompt, system_prompt)
                breaker.record_success()
                self.cache.set(prompt, result)
                return {
                    "content": result,
                    "provider": provider.value,
                    "cache_hit": None,
                }
            except Exception as e:
                logger.error(f"Provider {provider.value} failed: {e}")
                breaker.record_failure()

        raise RuntimeError("All LLM providers exhausted or circuit-broken")

    async def _simulate_provider_call(self, provider: Provider, prompt: str, system_prompt: str | None) -> str:
        """Simulate upstream LLM call with structured output reasoning."""
        await asyncio.sleep(0.01)  # Minimal latency simulation
        if "BUY" in prompt.upper() or "BULLISH" in prompt.upper():
            return '{"action": "BUY", "quantity": 100, "confidence": 0.88, "reasoning": "Strong bullish momentum and positive news sentiment."}'
        if "SELL" in prompt.upper() or "BEARISH" in prompt.upper():
            return '{"action": "SELL", "quantity": 50, "confidence": 0.82, "reasoning": "Bearish MACD crossover and negative earnings revision."}'
        return '{"action": "HOLD", "quantity": 0, "confidence": 0.95, "reasoning": "Consolidating market range; preserving capital."}'
