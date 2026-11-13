"""Cryptographic HMAC-SHA256 signature verification for human-in-the-loop trade approvals."""

import hashlib
import hmac
import time

from durable_agent.config import settings


class CryptoApprovalSigner:
    """Issues and cryptographically validates tamper-evident approval tokens."""

    def __init__(self, secret_key: str | None = None) -> None:
        self.secret_key = (secret_key or settings.hmac_secret_key).encode("utf-8")

    def generate_token(self, workflow_id: str, action: str, notional_usd: float, expiry_seconds: int = 3600) -> str:
        """Create a signed token binding the trade parameters, workflow ID, and expiration timestamp."""
        expires_at = int(time.time()) + expiry_seconds
        payload = f"{workflow_id}:{action}:{notional_usd:.2f}:{expires_at}"
        signature = hmac.new(self.secret_key, payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{payload}:{signature}"

    def verify_token(self, token: str, expected_workflow_id: str, expected_action: str) -> tuple[bool, str]:
        """Validate token integrity, expiration, and parameter matching."""
        parts = token.split(":")
        if len(parts) != 5:
            return False, "Invalid token format; expected 5 colon-separated fields"

        workflow_id, action, notional_str, expires_at_str, received_sig = parts

        if workflow_id != expected_workflow_id:
            return False, f"Workflow ID mismatch: token={workflow_id}, expected={expected_workflow_id}"

        if action.upper() != expected_action.upper():
            return False, f"Action mismatch: token={action}, expected={expected_action}"

        try:
            expires_at = int(expires_at_str)
            if time.time() > expires_at:
                return False, "Approval token has expired"
        except ValueError:
            return False, "Invalid expiration timestamp"

        payload = f"{workflow_id}:{action}:{notional_str}:{expires_at_str}"
        expected_sig = hmac.new(self.secret_key, payload.encode("utf-8"), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(expected_sig, received_sig):
            return False, "Cryptographic signature verification failed (tampered payload)"

        return True, "Valid approval signature"
