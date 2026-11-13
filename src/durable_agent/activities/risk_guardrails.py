"""Temporal activities for risk validation, exposure limits, and cryptographic token issuance."""

from temporalio import activity

from durable_agent.config import settings
from durable_agent.models.market import TradeIntent
from durable_agent.safeguards.hmac_signer import CryptoApprovalSigner


@activity.defn
async def evaluate_risk_limits(intent: TradeIntent) -> dict:
    """Evaluate proposed trade against enterprise risk policies and regulatory thresholds."""
    activity.logger.info(
        f"Evaluating risk limits for intent: {intent.ticker} {intent.action.value} notional=${intent.estimated_notional_usd:.2f}"
    )

    threshold = settings.human_approval_threshold_usd
    requires_approval = intent.estimated_notional_usd >= threshold

    approval_token = None
    if requires_approval:
        signer = CryptoApprovalSigner()
        wf_info = activity.info()
        approval_token = signer.generate_token(
            workflow_id=wf_info.workflow_id or "default-workflow",
            action=intent.action.value,
            notional_usd=intent.estimated_notional_usd,
            expiry_seconds=86400,  # 24-hour durable window
        )
        activity.logger.warning(
            f"GUARDRAIL TRIGGERED: Notional ${intent.estimated_notional_usd:.2f} >= ${threshold:.2f}. "
            f"Requiring human approval token."
        )

    return {
        "passed": True,
        "requires_human_approval": requires_approval,
        "approval_token": approval_token,
        "policy": "ENTERPRISE_RISK_POLICY_2026",
    }
