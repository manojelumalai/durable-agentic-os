"""End-to-End runnable demonstration of the Autonomous Trading Desk Workflow.
Runs an in-memory Temporal execution environment, fans out parallel strategy backtests,
evaluates live market and news sentiment, triggers the risk guardrail, sends a cryptographic
HMAC approval signal, and executes an idempotent order.
"""

import asyncio
from collections.abc import Callable
from typing import Any

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


async def main() -> None:
    print("=" * 75)
    print("🚀 DURABLE AGENTIC OS: THE AUTONOMOUS TRADING DESK THAT NEVER FAILS")
    print("=" * 75)

    print("\n1. Initializing Temporal In-Memory Test Server...")
    async with await WorkflowEnvironment.start_time_skipping(data_converter=pydantic_data_converter) as env:
        task_queue = "demo-trading-desk-queue"

        activities_list: list[Callable[..., Any]] = [
            fetch_market_snapshot,
            fetch_news_snapshot,
            run_backtest_strategy,
            evaluate_risk_limits,
            execute_order_idempotent,
            record_audit_log,
        ]
        async with Worker(
            env.client,
            task_queue=task_queue,
            workflows=[AutonomousTradingDeskWorkflow],
            activities=activities_list,
        ):
            workflow_id = "wf-trading-desk-live-01"
            ticker = "NVDA"

            # Pre-generate valid HMAC approval token for trade exceeding $10,000 threshold
            signer = CryptoApprovalSigner()
            approval_token = signer.generate_token(
                workflow_id=workflow_id,
                action="BUY",
                notional_usd=15000.0,
            )

            print(f"2. Submitting Workflow for ticker: {ticker}")
            print(f"   Task Queue: {task_queue} | Workflow ID: {workflow_id}")
            handle = await env.client.start_workflow(
                AutonomousTradingDeskWorkflow.run,
                TradingDeskInput(ticker=ticker, max_ticks=1, tick_interval_sec=0.2),
                id=workflow_id,
                task_queue=task_queue,
                start_signal="approve_trade",
                start_signal_args=[approval_token],
            )

            print("3. Executing Phase 1: Fan-out N parallel backtests in sandboxes...")
            print("4. Executing Phase 2: Live Market / News evaluation & Trade Intent generation...")
            print("5. Evaluating Risk Guardrails: Trade > $10,000 triggered cryptographic approval hold...")
            print(f"   Cryptographic Approval Token: {approval_token[:30]}...")

            result = await handle.result()

            print("\n" + "=" * 75)
            print("✅ WORKFLOW EXECUTION COMPLETED")
            print("=" * 75)
            print(f"Final Status:      {result['status']}")
            print(f"Winning Strategy:  {result['active_strategy']}")
            print(f"Total Ticks:       {result['ticks']}")
            print(f"Executed Orders:   {len(result['executed_orders'])}")
            print(f"Total Events Logged: {result['total_events']}")

            for idx, order in enumerate(result["executed_orders"], start=1):
                print(f"\nOrder #{idx}:")
                print(f"  Order ID:        {order['order_id']}")
                print(f"  Action:          {order['action']} {order['executed_quantity']} shares")
                print(f"  Execution Price: ${order['execution_price']:.2f}")
                print(f"  Notional Value:  ${order['notional_usd']:,.2f} USD")
                print(f"  Latency:         {order['execution_latency_ms']} ms")
                print(f"  Status:          {order['status']}")


if __name__ == "__main__":
    asyncio.run(main())
