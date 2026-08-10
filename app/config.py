from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_webhook_secret: str = Field(default="", alias="TELEGRAM_WEBHOOK_SECRET")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    llm_model: str = Field(default="gemini-2.5-flash", alias="LLM_MODEL")
    finnhub_api_key: str = Field(default="", alias="FINNHUB_API_KEY")
    news_api_key: str = Field(default="", alias="NEWS_API_KEY")
    max_tool_calls: int = Field(default=8, alias="MAX_TOOL_CALLS")
    http_timeout_seconds: float = Field(default=15.0, alias="HTTP_TIMEOUT_SECONDS")
    sec_user_agent: str = Field(default="Atlas Financial Assistant", alias="SEC_USER_AGENT")
    sec_contact_email: str = Field(default="contact@example.com", alias="SEC_CONTACT_EMAIL")
    database_url: str = Field(default="postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/AtlasAI", alias="DATABASE_URL")
    app_env: str = Field(default="development", alias="APP_ENV")
    conversation_context_limit: int = Field(default=12, alias="CONVERSATION_CONTEXT_LIMIT")
    
    # Milestone 4 Configuration
    briefing_importance_threshold: float = Field(default=0.75, alias="BRIEFING_IMPORTANCE_THRESHOLD")
    scheduler_enabled: bool = Field(default=True, alias="SCHEDULER_ENABLED")
    scheduler_poll_interval_seconds: int = Field(default=30, alias="SCHEDULER_POLL_INTERVAL_SECONDS")
    max_briefing_articles: int = Field(default=10, alias="MAX_BRIEFING_ARTICLES")
    max_watchlist_items_per_briefing: int = Field(default=20, alias="MAX_WATCHLIST_ITEMS_PER_BRIEFING")

    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8-sig", extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()
