"""Unit tests for MultiProviderLLMGateway and CircuitBreaker."""

import pytest

from durable_agent.llm.gateway import (
    CircuitBreaker,
    CircuitState,
    MultiProviderLLMGateway,
    Provider,
)


def test_circuit_breaker_state_transitions() -> None:
    breaker = CircuitBreaker(failure_threshold=2, reset_timeout_sec=0.05)
    assert breaker.state == CircuitState.CLOSED
    assert breaker.allow_request() is True

    breaker.record_failure()
    assert breaker.state == CircuitState.CLOSED

    breaker.record_failure()
    assert breaker.state == CircuitState.OPEN
    assert breaker.allow_request() is False


@pytest.mark.asyncio
async def test_llm_gateway_complete_bullish_prompt() -> None:
    gateway = MultiProviderLLMGateway()
    res = await gateway.complete("Generate trade intent for NVDA based on strong bullish momentum")

    assert res["provider"] == Provider.OPENAI.value
    assert "BUY" in res["content"]


@pytest.mark.asyncio
async def test_llm_gateway_caching_on_subsequent_call() -> None:
    gateway = MultiProviderLLMGateway()
    prompt = "Predict earnings move for AAPL"

    # Call 1 -> Hits Provider
    res1 = await gateway.complete(prompt)
    assert res1["provider"] == Provider.OPENAI.value

    # Call 2 -> Hits Cache
    res2 = await gateway.complete(prompt)
    assert res2["provider"] == "cache"
    assert res2["cache_hit"] == "exact"
