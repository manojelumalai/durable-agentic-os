"""Unit tests for cryptographic HMAC-SHA256 human approval safeguards."""

from durable_agent.safeguards.hmac_signer import CryptoApprovalSigner


def test_hmac_token_valid_generation_and_verification() -> None:
    signer = CryptoApprovalSigner(secret_key="test-secret")
    token = signer.generate_token(workflow_id="wf-123", action="BUY", notional_usd=15000.0, expiry_seconds=300)

    valid, msg = signer.verify_token(token, expected_workflow_id="wf-123", expected_action="BUY")
    assert valid is True
    assert "Valid" in msg


def test_hmac_token_tampered_payload_rejected() -> None:
    signer = CryptoApprovalSigner(secret_key="test-secret")
    token = signer.generate_token(workflow_id="wf-123", action="BUY", notional_usd=15000.0, expiry_seconds=300)

    # Tamper with the notional amount: 15000.00 -> 25000.00
    parts = token.split(":")
    parts[2] = "25000.00"
    tampered_token = ":".join(parts)

    valid, msg = signer.verify_token(tampered_token, expected_workflow_id="wf-123", expected_action="BUY")
    assert valid is False
    assert "signature verification failed" in msg.lower()


def test_hmac_token_action_mismatch() -> None:
    signer = CryptoApprovalSigner(secret_key="test-secret")
    token = signer.generate_token(workflow_id="wf-123", action="BUY", notional_usd=15000.0)

    valid, msg = signer.verify_token(token, expected_workflow_id="wf-123", expected_action="SELL")
    assert valid is False
    assert "Action mismatch" in msg


def test_hmac_token_workflow_id_mismatch() -> None:
    signer = CryptoApprovalSigner(secret_key="test-secret")
    token = signer.generate_token(workflow_id="wf-123", action="BUY", notional_usd=15000.0)

    valid, msg = signer.verify_token(token, expected_workflow_id="wf-999", expected_action="BUY")
    assert valid is False
    assert "Workflow ID mismatch" in msg


def test_hmac_token_expired() -> None:
    signer = CryptoApprovalSigner(secret_key="test-secret")
    # Expired token with negative expiry
    token = signer.generate_token(workflow_id="wf-123", action="BUY", notional_usd=15000.0, expiry_seconds=-10)

    valid, msg = signer.verify_token(token, expected_workflow_id="wf-123", expected_action="BUY")
    assert valid is False
    assert "expired" in msg.lower()
