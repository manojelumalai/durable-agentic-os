"""Unit tests for Temporal activities."""

import pytest

from durable_agent.activities.market_tools import (
    fetch_market_snapshot,
    fetch_news_snapshot,
    run_backtest_strategy,
)
from durable_agent.activities.order_execution import execute_order_idempotent
from durable_agent.activities.risk_guardrails import evaluate_risk_limits
from durable_agent.models.market import OrderAction, OrderStatus, TradeIntent
from durable_agent.models.state import BacktestCandidate


@pytest.mark.asyncio
async def test_fetch_market_snapshot() -> None:
    snapshot = await fetch_market_snapshot("NVDA")
    assert snapshot.ticker == "NVDA"
    assert snapshot.price > 0.0
    assert snapshot.high_24h >= snapshot.price
    assert snapshot.low_24h <= snapshot.price


@pytest.mark.asyncio
async def test_fetch_news_snapshot() -> None:
    news = await fetch_news_snapshot("NVDA")
    assert news.ticker == "NVDA"
    assert -1.0 <= news.sentiment_score <= 1.0
    assert len(news.top_headline) > 0


@pytest.mark.asyncio
async def test_run_backtest_strategy() -> None:
    candidate = BacktestCandidate(
        strategy_id="test-momentum",
        name="Momentum Alpha",
        parameters={"risk_factor": 1.2},
    )
    result = await run_backtest_strategy(candidate)
    assert result.strategy_id == "test-momentum"
    assert result.sharpe_ratio > 0.0
    assert result.total_return_pct > 0.0
    assert result.win_rate_pct > 0.0


@pytest.mark.asyncio
async def test_evaluate_risk_limits_small_trade() -> None:
    intent = TradeIntent(
        ticker="NVDA",
        action=OrderAction.BUY,
        quantity=20.0,
        price_target=150.0,
        confidence_score=0.9,
        reasoning="Test",
    )
    intent.compute_notional()  # $3,000 < $10,000 threshold

    res = await evaluate_risk_limits(intent)
    assert res["passed"] is True
    assert res["requires_human_approval"] is False
    assert res["approval_token"] is None


@pytest.mark.asyncio
async def test_execute_order_idempotent() -> None:
    order = await execute_order_idempotent(
        workflow_id="wf-test-01",
        ticker="NVDA",
        action=OrderAction.BUY,
        quantity=50.0,
        price=150.0,
    )
    assert order.status == OrderStatus.EXECUTED
    assert order.executed_quantity == 50.0
    assert order.notional_usd == 7500.0
    assert order.idempotency_key is not None
