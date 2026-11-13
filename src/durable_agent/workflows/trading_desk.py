"""Durable Autonomous Trading Desk Workflow.
Implements the SuperAI architecture: parallel backtest fanout, durable multi-turn agent loop,
and cryptographic human-in-the-loop approval gates that survive process crashes.
"""

import asyncio
from datetime import timedelta
from typing import Any

from pydantic import BaseModel, Field
from temporalio import workflow
from temporalio.common import RetryPolicy

# Import activities inside workflow with type safety
with workflow.unsafe.imports_passed_through():
    from durable_agent.activities.market_tools import (
        fetch_market_snapshot,
        fetch_news_snapshot,
        run_backtest_strategy,
    )
    from durable_agent.activities.order_execution import (
        execute_order_idempotent,
        record_audit_log,
    )
    from durable_agent.activities.risk_guardrails import evaluate_risk_limits
    from durable_agent.models.events import AgentEvent, EventType
    from durable_agent.models.market import (
        MarketSnapshot,
        NewsSnapshot,
        OrderAction,
        OrderResult,
        TradeIntent,
    )
    from durable_agent.models.state import BacktestCandidate, BacktestResult, Phase
    from durable_agent.safeguards.hmac_signer import CryptoApprovalSigner


class TradingDeskInput(BaseModel):
    """Input payload to start the Autonomous Trading Desk workflow."""

    ticker: str = "NVDA"
    candidate_strategies: list[BacktestCandidate] = Field(default_factory=list)
    max_ticks: int = 5
    tick_interval_sec: float = 1.0
    auto_execute_small_trades: bool = True


@workflow.defn
class AutonomousTradingDeskWorkflow:
    """The Autonomous Trading Desk that Never Fails.
    Durable Temporal workflow orchestrating multi-agent finance with cryptographic human oversight.
    """

    def __init__(self) -> None:
        self.phase: Phase = Phase.INITIALIZING
        self.tick_count: int = 0
        self.stopped: bool = False
        self.active_strategy: BacktestResult | None = None
        self.current_market: MarketSnapshot | None = None
        self.current_news: NewsSnapshot | None = None
        self.last_trade_intent: TradeIntent | None = None
        self.executed_orders: list[OrderResult] = []
        self.events: list[dict[str, Any]] = []

        # Human-in-the-loop signal state
        self.approval_received: bool | None = None
        self.approval_token: str | None = None
        self.rejection_reason: str | None = None

        # Activity retry policy
        self._retry_policy = RetryPolicy(
            initial_interval=timedelta(milliseconds=200),
            backoff_coefficient=2.0,
            maximum_interval=timedelta(seconds=5),
            maximum_attempts=5,
        )

    def _emit(self, event_type: EventType, payload: dict[str, Any]) -> None:
        """Record structured event in workflow state."""
        evt = AgentEvent(
            event_id=f"EVT-{len(self.events) + 1:04d}",
            workflow_id=workflow.info().workflow_id,
            event_type=event_type,
            phase=self.phase.value,
            payload=payload,
        )
        self.events.append(evt.model_dump(mode="json"))

    @workflow.run
    async def run(self, inp: TradingDeskInput) -> dict[str, Any]:
        """Execute Phase 1 (Backtest Fanout) and Phase 2 (Autonomous Trade Loop)."""
        self._emit(EventType.PHASE_CHANGE, {"from": self.phase.value, "to": Phase.DISCOVERING.value})
        self.phase = Phase.DISCOVERING

        # ─────────────────────────────────────────────────────────────
        # Phase 1: Fan out parallel backtests in sandboxes
        # ─────────────────────────────────────────────────────────────
        strategies = inp.candidate_strategies or [
            BacktestCandidate(strategy_id="strat-alpha", name="Mean Reversion", parameters={"risk_factor": 1.2}),
            BacktestCandidate(strategy_id="strat-beta", name="Momentum Breakout", parameters={"risk_factor": 1.5}),
            BacktestCandidate(strategy_id="strat-gamma", name="VWAP Institutional", parameters={"risk_factor": 0.9}),
            BacktestCandidate(strategy_id="strat-delta", name="Sentiment Trend", parameters={"risk_factor": 1.1}),
        ]

        self._emit(EventType.TOOL_CALL_STARTED, {"tool": "run_backtest_strategy", "fanout_count": len(strategies)})

        backtest_tasks = [
            workflow.execute_activity(
                run_backtest_strategy,
                strat,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=self._retry_policy,
            )
            for strat in strategies
        ]

        results: list[BacktestResult] = await asyncio.gather(*backtest_tasks)

        # Deterministically select the highest Sharpe ratio strategy with max drawdown < 15%
        valid_results = [r for r in results if r.max_drawdown_pct < 15.0]
        winner = max(valid_results or results, key=lambda r: r.sharpe_ratio)
        self.active_strategy = winner

        self._emit(
            EventType.PHASE_CHANGE,
            {
                "phase": Phase.SYNTHESIZING.value,
                "winning_strategy": winner.strategy_id,
                "sharpe": winner.sharpe_ratio,
            },
        )
        self.phase = Phase.SYNTHESIZING

        # ─────────────────────────────────────────────────────────────
        # Phase 2: Autonomous Trade Loop
        # ─────────────────────────────────────────────────────────────
        while self.tick_count < inp.max_ticks and not self.stopped:
            self.tick_count += 1
            self._emit(EventType.TURN_START, {"tick": self.tick_count, "ticker": inp.ticker})

            # Step 1: Fetch Market Snapshot Activity
            self.current_market = await workflow.execute_activity(
                fetch_market_snapshot,
                inp.ticker,
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=self._retry_policy,
            )

            # Step 2: Fetch News Snapshot Activity
            self.current_news = await workflow.execute_activity(
                fetch_news_snapshot,
                inp.ticker,
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=self._retry_policy,
            )

            # Step 3: Synthesize Trade Intent
            # (In production, invokes LLM Agent via gateway activity)
            price = self.current_market.price
            action = OrderAction.BUY if self.current_news.sentiment_score > 0.5 else OrderAction.HOLD
            quantity = 100.0 if action == OrderAction.BUY else 0.0

            intent = TradeIntent(
                ticker=inp.ticker,
                action=action,
                quantity=quantity,
                price_target=price,
                confidence_score=0.91,
                reasoning=f"Sentiment score {self.current_news.sentiment_score:.2f} bullish; price ${price:.2f} near VWAP.",
            )
            intent.compute_notional()
            self.last_trade_intent = intent

            if action == OrderAction.HOLD:
                self._emit(EventType.WORKFLOW_COMPLETED, {"action": "HOLD", "reason": "No trade signal triggered"})
                await workflow.sleep(timedelta(seconds=inp.tick_interval_sec))
                continue

            # Step 4: Evaluate Risk Limits Activity
            risk_eval: dict = await workflow.execute_activity(
                evaluate_risk_limits,
                intent,
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=self._retry_policy,
            )

            # Step 5: Guardrail Check — Human-in-the-Loop Signal
            if risk_eval.get("requires_human_approval"):
                self.phase = Phase.AWAITING_APPROVAL
                token = risk_eval.get("approval_token")
                self._emit(
                    EventType.APPROVAL_REQUESTED,
                    {
                        "notional_usd": intent.estimated_notional_usd,
                        "threshold": 10000.0,
                        "approval_token": token,
                    },
                )

                # Workflow halts safely with ZERO CPU consumption until signal arrives
                await workflow.wait_condition(lambda: self.approval_received is not None or self.stopped)

                if self.stopped:
                    break

                if not self.approval_received:
                    self._emit(
                        EventType.APPROVAL_REJECTED,
                        {"reason": self.rejection_reason or "Trade rejected by risk officer"},
                    )
                    await workflow.execute_activity(
                        record_audit_log,
                        args=[workflow.info().workflow_id, "TRADE_REJECTED", {"intent": intent.model_dump()}],
                        start_to_close_timeout=timedelta(seconds=10),
                    )
                    await workflow.sleep(timedelta(seconds=inp.tick_interval_sec))
                    continue

                # Verify cryptographic token signature
                signer = CryptoApprovalSigner()
                valid, msg = signer.verify_token(
                    token=self.approval_token or "",
                    expected_workflow_id=workflow.info().workflow_id,
                    expected_action=intent.action.value,
                )
                if not valid:
                    self._emit(EventType.GUARDRAIL_TRIGGERED, {"error": f"Crypto verification failed: {msg}"})
                    continue

                self._emit(EventType.APPROVAL_RECEIVED, {"token_verified": True})
                # Reset approval signal for subsequent ticks
                self.approval_received = None
                self.approval_token = None

            # Step 6: Idempotent Order Execution
            self.phase = Phase.EXECUTING
            order_res: OrderResult = await workflow.execute_activity(
                execute_order_idempotent,
                args=[workflow.info().workflow_id, intent.ticker, intent.action, intent.quantity, intent.price_target],
                start_to_close_timeout=timedelta(seconds=15),
                retry_policy=self._retry_policy,
            )
            self.executed_orders.append(order_res)
            self._emit(EventType.ORDER_EXECUTED, order_res.model_dump(mode="json"))

            # Step 7: Durable Sleep for next tick
            await workflow.sleep(timedelta(seconds=inp.tick_interval_sec))

        self.phase = Phase.COMPLETED
        return {
            "status": "COMPLETED",
            "ticks": self.tick_count,
            "active_strategy": self.active_strategy.strategy_id if self.active_strategy else None,
            "executed_orders": [o.model_dump(mode="json") for o in self.executed_orders],
            "total_events": len(self.events),
        }

    # ─────────────────────────────────────────────────────────────
    # Temporal Signals & Queries
    # ─────────────────────────────────────────────────────────────

    @workflow.signal
    def approve_trade(self, token: str) -> None:
        """Signal sent by human or risk system approving a held high-value trade."""
        self.approval_received = True
        self.approval_token = token

    @workflow.signal
    def reject_trade(self, reason: str) -> None:
        """Signal sent rejecting a pending trade."""
        self.approval_received = False
        self.rejection_reason = reason

    @workflow.signal
    def stop_workflow(self) -> None:
        """Signal to gracefully stop the trading desk loop."""
        self.stopped = True

    @workflow.query
    def get_current_state(self) -> dict[str, Any]:
        """Query workflow state without mutating event history."""
        return {
            "phase": self.phase.value,
            "tick_count": self.tick_count,
            "stopped": self.stopped,
            "active_strategy": self.active_strategy.model_dump() if self.active_strategy else None,
            "last_trade_intent": self.last_trade_intent.model_dump() if self.last_trade_intent else None,
            "orders_count": len(self.executed_orders),
            "events_count": len(self.events),
        }

    @workflow.query
    def get_events(self) -> list[dict[str, Any]]:
        """Query stream of structured agent events."""
        return self.events
