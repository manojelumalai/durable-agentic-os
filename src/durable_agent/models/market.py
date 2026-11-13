"""Domain models for market data, news sentiment, trade intent, and order execution."""

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class OrderAction(str, Enum):
    """Trading action proposed by the agent."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class OrderStatus(str, Enum):
    """Lifecycle state of an executed order."""

    PENDING = "PENDING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"


class MarketSnapshot(BaseModel):
    """Current market data point for a given ticker symbol."""

    ticker: str
    price: float
    volume_24h: float
    high_24h: float
    low_24h: float
    vwap: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class NewsSnapshot(BaseModel):
    """Aggregated financial news sentiment and headlines."""

    ticker: str
    sentiment_score: float = Field(..., ge=-1.0, le=1.0, description="-1.0 (bearish) to +1.0 (bullish)")
    headline_count: int
    top_headline: str
    source: str = "financial_wire"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TradeIntent(BaseModel):
    """Structured decision output produced by the LLM trading agent."""

    ticker: str
    action: OrderAction
    quantity: float
    price_target: float
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
    requires_approval: bool = False
    estimated_notional_usd: float = 0.0

    def compute_notional(self) -> float:
        """Calculate total trade value in USD."""
        self.estimated_notional_usd = round(self.quantity * self.price_target, 2)
        return self.estimated_notional_usd


class OrderResult(BaseModel):
    """Confirmation output after order routing and execution."""

    order_id: str
    idempotency_key: str
    ticker: str
    action: OrderAction
    executed_quantity: float
    execution_price: float
    status: OrderStatus
    notional_usd: float
    execution_latency_ms: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
