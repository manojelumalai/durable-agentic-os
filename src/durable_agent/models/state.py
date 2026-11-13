"""State representations for backtests and durable workflow tracking."""

from enum import Enum

from pydantic import BaseModel, Field

from durable_agent.models.events import AgentEvent
from durable_agent.models.market import OrderResult, TradeIntent


class Phase(str, Enum):
    """Phases corresponding to the SuperAI Autonomous Trading Desk execution."""

    INITIALIZING = "INITIALIZING"
    DISCOVERING = "DISCOVERING"
    SYNTHESIZING = "SYNTHESIZING"
    EVALUATING = "EVALUATING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class BacktestCandidate(BaseModel):
    """Specification of an algorithmic strategy candidate to evaluate in parallel."""

    strategy_id: str
    name: str
    parameters: dict[str, float] = Field(default_factory=dict)


class BacktestResult(BaseModel):
    """Observed backtest simulation performance metrics."""

    strategy_id: str
    sharpe_ratio: float
    max_drawdown_pct: float
    total_return_pct: float
    win_rate_pct: float
    sandboxed_duration_ms: float


class DurableTradingState(BaseModel):
    """Complete serializable state persisted in Temporal Event History."""

    workflow_id: str
    phase: Phase = Phase.INITIALIZING
    ticker: str
    active_strategy_id: str | None = None
    tick_count: int = 0
    trade_intents: list[TradeIntent] = Field(default_factory=list)
    executed_orders: list[OrderResult] = Field(default_factory=list)
    events: list[AgentEvent] = Field(default_factory=list)
    pending_approval_token: str | None = None
    stopped: bool = False
