"""Structured AgentEvents stream models matching the SuperAI Agent Harness specification."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Categorization of agent execution events."""

    PHASE_CHANGE = "phase_change"
    TURN_START = "turn_start"
    TOOL_CALL_STARTED = "tool_call_started"
    TOOL_CALL_COMPLETED = "tool_call_completed"
    TOOL_CALL_FAILED = "tool_call_failed"
    GUARDRAIL_TRIGGERED = "guardrail_triggered"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_RECEIVED = "approval_received"
    APPROVAL_REJECTED = "approval_rejected"
    ORDER_SUBMITTED = "order_submitted"
    ORDER_EXECUTED = "order_executed"
    WORKFLOW_COMPLETED = "workflow_completed"


class AgentEvent(BaseModel):
    """Observable structured event emitted by durable agent workflows."""

    event_id: str = Field(..., description="Unique event identifier")
    workflow_id: str = Field(..., description="Temporal workflow execution ID")
    event_type: EventType = Field(..., description="Type of event")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    phase: str = Field(..., description="Active workflow phase (e.g., DISCOVERY, TRADING)")
    payload: dict[str, Any] = Field(default_factory=dict, description="Event data attributes")
