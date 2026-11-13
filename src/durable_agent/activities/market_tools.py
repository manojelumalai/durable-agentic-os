"""Temporal activities for market data retrieval, news feeds, and parallel backtesting."""

import asyncio

from temporalio import activity

from durable_agent.models.market import MarketSnapshot, NewsSnapshot
from durable_agent.models.state import BacktestCandidate, BacktestResult


@activity.defn
async def fetch_market_snapshot(ticker: str) -> MarketSnapshot:
    """Fetch current market pricing, volume, and VWAP for a ticker symbol."""
    activity.logger.info(f"Executing fetch_market_snapshot for ticker: {ticker}")
    await asyncio.sleep(0.02)  # Simulated I/O latency

    # Deterministic simulated base price by ticker
    base_price = 150.0 if "NVDA" in ticker else 220.0 if "AAPL" in ticker else 180.0
    jitter = (hash(ticker) % 100) / 50.0 - 1.0  # -1.0 to +1.0
    price = round(base_price + jitter, 2)

    return MarketSnapshot(
        ticker=ticker,
        price=price,
        volume_24h=14500000.0,
        high_24h=price * 1.03,
        low_24h=price * 0.97,
        vwap=price * 0.998,
    )


@activity.defn
async def fetch_news_snapshot(ticker: str) -> NewsSnapshot:
    """Fetch aggregated news headlines and NLP sentiment analysis score."""
    activity.logger.info(f"Executing fetch_news_snapshot for ticker: {ticker}")
    await asyncio.sleep(0.02)

    return NewsSnapshot(
        ticker=ticker,
        sentiment_score=0.74,
        headline_count=18,
        top_headline=f"{ticker} announces enterprise autonomous AI platform partnership; revenue guidance raised.",
        source="Bloomberg Terminal API",
    )


@activity.defn
async def run_backtest_strategy(candidate: BacktestCandidate) -> BacktestResult:
    """Run an air-gapped historical backtest simulation for a single candidate strategy."""
    activity.logger.info(f"Executing sandboxed backtest for strategy: {candidate.name}")
    start = asyncio.get_event_loop().time()
    await asyncio.sleep(0.03)  # Simulated backtest calculation

    # Deterministic calculation based on strategy parameter
    factor = candidate.parameters.get("risk_factor", 1.0)
    sharpe = round(1.85 + (hash(candidate.strategy_id) % 50) / 100.0 * factor, 2)
    win_rate = round(58.0 + (hash(candidate.strategy_id) % 15), 1)

    elapsed_ms = (asyncio.get_event_loop().time() - start) * 1000

    return BacktestResult(
        strategy_id=candidate.strategy_id,
        sharpe_ratio=sharpe,
        max_drawdown_pct=round(7.5 / factor, 2),
        total_return_pct=round(24.5 * factor, 2),
        win_rate_pct=win_rate,
        sandboxed_duration_ms=round(elapsed_ms, 2),
    )
