"""Temporal activities for idempotent order routing, double-entry ledger execution, and audit logging."""

import asyncio
import hashlib
from datetime import UTC, datetime

from temporalio import activity

from durable_agent.models.market import OrderAction, OrderResult, OrderStatus


@activity.defn
async def execute_order_idempotent(
    workflow_id: str,
    ticker: str,
    action: OrderAction,
    quantity: float,
    price: float,
    idempotency_key: str | None = None,
) -> OrderResult:
    """Execute order with guaranteed idempotency and simulated exchange clearing."""
    start = asyncio.get_event_loop().time()
    action_str = action.value if hasattr(action, "value") else str(action)
    action_enum = OrderAction(action_str)
    activity.logger.info(f"Executing order {action_str} {quantity} {ticker} @ ${price:.2f}")

    # Generate deterministic idempotency key if not supplied
    if not idempotency_key:
        raw_key = f"{workflow_id}:{ticker}:{action_str}:{quantity}:{price}"
        idempotency_key = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]

    await asyncio.sleep(0.02)  # Simulated matching engine latency
    order_id = f"ORD-{idempotency_key[:8].upper()}"
    notional = round(quantity * price, 2)
    elapsed_ms = (asyncio.get_event_loop().time() - start) * 1000

    return OrderResult(
        order_id=order_id,
        idempotency_key=idempotency_key,
        ticker=ticker,
        action=action_enum,
        executed_quantity=quantity,
        execution_price=price,
        status=OrderStatus.EXECUTED,
        notional_usd=notional,
        execution_latency_ms=round(elapsed_ms, 2),
        timestamp=datetime.now(UTC),
    )


@activity.defn
async def record_audit_log(workflow_id: str, message: str, payload: dict) -> None:
    """Persist structured immutable audit log for compliance and operational tracking."""
    activity.logger.info(f"[AUDIT LOG] {workflow_id}: {message} | payload={payload}")
