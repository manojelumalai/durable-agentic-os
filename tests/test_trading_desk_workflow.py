"""Integration test for Autonomous Trading Desk Temporal workflow using Temporal Time-Skipping Test Server."""

import pytest
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

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
from durable_agent.safeguards.hmac_signer import CryptoApprovalSigner
from durable_agent.workflows.trading_desk import AutonomousTradingDeskWorkflow, TradingDeskInput


@pytest.mark.asyncio
async def test_trading_desk_workflow_execution_and_approval_signal() -> None:
    """Test full workflow cycle: Phase 1 fanout, Phase 2 trade intent, guardrail hold, and signal approval."""
    async with await WorkflowEnvironment.start_time_skipping(data_converter=pydantic_data_converter) as env:
        task_queue = "test-trading-queue"

        async with Worker(
            env.client,
            task_queue=task_queue,
            workflows=[AutonomousTradingDeskWorkflow],
            activities=[
                fetch_market_snapshot,
                fetch_news_snapshot,
                run_backtest_strategy,
                evaluate_risk_limits,
                execute_order_idempotent,
                record_audit_log,
            ],
        ):
            # Generate valid cryptographic HMAC approval token for signal
            signer = CryptoApprovalSigner()
            approval_token = signer.generate_token(
                workflow_id="test-trading-workflow-01",
                action="BUY",
                notional_usd=15000.0,
            )

            # Start workflow with approval signal
            handle = await env.client.start_workflow(
                AutonomousTradingDeskWorkflow.run,
                TradingDeskInput(ticker="NVDA", max_ticks=1, tick_interval_sec=0.1),
                id="test-trading-workflow-01",
                task_queue=task_queue,
                start_signal="approve_trade",
                start_signal_args=[approval_token],
            )
            # Await workflow completion
            result = await handle.result()

            assert result["status"] == "COMPLETED"
            assert result["ticks"] == 1
            assert result["active_strategy"] is not None
            assert len(result["executed_orders"]) >= 1
            assert result["total_events"] > 0
