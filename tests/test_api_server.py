"""Unit tests for FastAPI operational endpoints."""

from fastapi.testclient import TestClient

from durable_agent.api.server import app

client = TestClient(app)


def test_api_health_check() -> None:
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_api_start_workflow() -> None:
    payload = {"ticker": "NVDA", "max_ticks": 3, "tick_interval_sec": 0.5}
    res = client.post("/api/v1/workflows/start", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "STARTED"
    assert data["ticker"] == "NVDA"
    assert "workflow_id" in data


def test_api_generate_and_verify_approval_token() -> None:
    # 1. Generate token
    gen_res = client.post(
        "/api/v1/safeguards/generate-approval-token",
        params={"workflow_id": "wf-test-api", "action": "BUY", "notional_usd": 18500.0},
    )
    assert gen_res.status_code == 200
    token = gen_res.json()["token"]

    # 2. Verify token
    verify_res = client.post(
        "/api/v1/safeguards/verify-approval-token",
        params={"token": token, "workflow_id": "wf-test-api", "action": "BUY"},
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["valid"] is True


def test_api_verify_invalid_token_fails() -> None:
    verify_res = client.post(
        "/api/v1/safeguards/verify-approval-token",
        params={"token": "invalid:token:format", "workflow_id": "wf-test-api", "action": "BUY"},
    )
    assert verify_res.status_code == 400
