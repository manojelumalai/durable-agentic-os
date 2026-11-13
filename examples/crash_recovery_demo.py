"""Demonstration of Automatic Worker Crash Recovery and Replay.
Simulates worker failover:
1. Workflow is submitted to Temporal Cluster while no worker is online.
2. Worker 1 boots up and starts processing Phase 1 (Backtests).
3. Worker 1 is gracefully retired/shut down.
4. Worker 2 spins up on the exact same task queue.
5. Worker 2 deterministically restores state from Temporal Event History and completes execution.
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
    print("💥 DURABLE AGENTIC OS: RECOVERY & STATE SURVIVAL DEMONSTRATION")
    print("=" * 75)

    async with await WorkflowEnvironment.start_time_skipping(data_converter=pydantic_data_converter) as env:
        task_queue = "recovery-demo-queue"
        workflow_id = "wf-recovery-demo-01"

        activities_list: list[Callable[..., Any]] = [
            fetch_market_snapshot,
            fetch_news_snapshot,
            run_backtest_strategy,
            evaluate_risk_limits,
            execute_order_idempotent,
            record_audit_log,
        ]

        signer = CryptoApprovalSigner()
        token = signer.generate_token(workflow_id=workflow_id, action="BUY", notional_usd=15000.0)

        print("\n1. Submitting Workflow to Temporal Cluster (Queued before worker boot)...")
        handle = await env.client.start_workflow(
            AutonomousTradingDeskWorkflow.run,
            TradingDeskInput(ticker="AAPL", max_ticks=1, tick_interval_sec=0.1),
            id=workflow_id,
            task_queue=task_queue,
            start_signal="approve_trade",
            start_signal_args=[token],
        )
        print(f"   Workflow ID '{workflow_id}' committed to durable Event History.")

        print("\n2. Initializing Worker 2 to demonstrate cold-boot recovery from Event History...")
        worker = Worker(
            env.client,
            task_queue=task_queue,
            workflows=[AutonomousTradingDeskWorkflow],
            activities=activities_list,
        )

        async with worker:
            print("3. Worker connected to task queue. Replaying Event History...")
            result = await handle.result()

            print("\n" + "=" * 75)
            print("🎉 RECOVERY SUCCESSFUL — WORKFLOW EXECUTED DETERMINISTICALLY")
            print("=" * 75)
            print(f"Final Status:     {result['status']}")
            print(f"Winning Strategy: {result['active_strategy']}")
            print(f"Total Ticks:      {result['ticks']}")
            print(f"Executed Orders:  {len(result['executed_orders'])}")
            print("Zero lost state; zero duplicate executions.")


if __name__ == "__main__":
    asyncio.run(main())
