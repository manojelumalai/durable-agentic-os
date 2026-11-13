"""FastAPI management and observability server for Durable Agentic OS."""

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from durable_agent.config import settings
from durable_agent.safeguards.hmac_signer import CryptoApprovalSigner

app = FastAPI(
    title="Durable Agentic OS API",
    version="1.0.0",
    description="Operational API for managing Temporal agentic workflows, human approvals, and real-time observability.",
)


class StartWorkflowRequest(BaseModel):
    ticker: str = "NVDA"
    max_ticks: int = 5
    tick_interval_sec: float = 1.0


class ApproveTradeRequest(BaseModel):
    token: str


class RejectTradeRequest(BaseModel):
    reason: str = "Risk threshold exceeded"


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy", "service": "durable-agentic-os"}


@app.post("/api/v1/workflows/start")
async def start_workflow(req: StartWorkflowRequest) -> dict[str, Any]:
    """Trigger a new durable autonomous trading desk workflow on Temporal."""
    # In production with live Temporal cluster:
    # client = await Client.connect(settings.temporal_host)
    # handle = await client.start_workflow(...)
    simulated_id = f"wf-trading-{req.ticker.lower()}-001"
    return {
        "status": "STARTED",
        "workflow_id": simulated_id,
        "ticker": req.ticker,
        "max_ticks": req.max_ticks,
        "task_queue": settings.task_queue,
    }


@app.post("/api/v1/safeguards/generate-approval-token")
async def generate_token(workflow_id: str, action: str, notional_usd: float) -> dict[str, str]:
    """Generate a valid HMAC-SHA256 token for human approval verification."""
    signer = CryptoApprovalSigner()
    token = signer.generate_token(workflow_id, action, notional_usd)
    return {"token": token, "workflow_id": workflow_id, "action": action}


@app.post("/api/v1/safeguards/verify-approval-token")
async def verify_token(token: str, workflow_id: str, action: str) -> dict[str, Any]:
    """Verify validity and authenticity of an approval token."""
    signer = CryptoApprovalSigner()
    valid, msg = signer.verify_token(token, workflow_id, action)
    if not valid:
        raise HTTPException(status_code=400, detail=msg)
    return {"valid": True, "message": msg}
