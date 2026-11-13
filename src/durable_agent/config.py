"""Configuration settings for Durable Agentic OS."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for workflows, LLM gateways, and safeguards."""

    model_config = SettingsConfigDict(env_prefix="DURABLE_", env_file=".env", extra="ignore")

    app_name: str = "Durable Agentic OS"
    environment: str = "production"
    log_level: str = "INFO"

    # Temporal Settings
    temporal_host: str = Field(default="localhost:7233", description="Temporal server address")
    temporal_namespace: str = Field(default="default", description="Temporal namespace")
    task_queue: str = Field(default="trading-desk-queue", description="Default task queue")

    # Financial Safeguards & Guardrails
    human_approval_threshold_usd: float = Field(
        default=10000.0, description="Trade amount requiring human approval signal"
    )
    hmac_secret_key: str = Field(
        default="durable-agentic-os-super-secret-key-2026",
        description="Key used for cryptographic HMAC-SHA256 trade approval tokens",
    )

    # Multi-Provider LLM Gateway Settings
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None
    default_model: str = "gpt-4o"
    semantic_cache_similarity_threshold: float = Field(
        default=0.92, description="Cosine similarity threshold for semantic cache hits"
    )

    # Rate Limiting
    rate_limit_rpm: int = Field(default=120, description="Requests per minute per tenant")
    rate_limit_tpm: int = Field(default=100000, description="Tokens per minute per tenant")


settings = Settings()
