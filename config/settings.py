"""Application settings loaded from environment variables or .env file."""

from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Ensure .env is loaded
load_dotenv()


class Settings(BaseSettings):
    """Central configuration management for the AI Job Hunter system."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Provider selection
    llm_provider: Literal["gemini", "deepseek"] = Field(
        default="gemini",
        alias="LLM_PROVIDER",
        description="Active LLM provider: 'gemini' or 'deepseek'",
    )

    # Gemini Settings
    gemini_api_key: str | None = Field(
        default=None,
        alias="GEMINI_API_KEY",
        description="Google Gemini API key",
    )
    gemini_model: str = Field(
        default="gemini-2.5-flash",
        alias="GEMINI_MODEL",
        description="Google Gemini model name (e.g. gemini-2.5-flash)",
    )

    # DeepSeek Settings
    deepseek_api_key: str | None = Field(
        default=None,
        alias="DEEPSEEK_API_KEY",
        description="DeepSeek API key",
    )
    deepseek_model: str = Field(
        default="deepseek-chat",
        alias="DEEPSEEK_MODEL",
        description="DeepSeek model name",
    )
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com",
        alias="DEEPSEEK_BASE_URL",
        description="DeepSeek API base endpoint",
    )

    # Notion Settings
    notion_token: str | None = Field(
        default=None,
        alias="NOTION_TOKEN",
        description="Notion internal integration token",
    )
    notion_database_id: str | None = Field(
        default=None,
        alias="NOTION_DATABASE_ID",
        description="Notion database ID for storing jobs",
    )

    # Telegram Settings
    telegram_bot_token: str | None = Field(
        default=None,
        alias="TELEGRAM_BOT_TOKEN",
        description="Telegram bot token for notifications",
    )
    telegram_chat_id: str | None = Field(
        default=None,
        alias="TELEGRAM_CHAT_ID",
        description="Telegram chat or channel ID to receive alerts",
    )

    # Evaluation Threshold
    fit_score_threshold: int = Field(
        default=75,
        alias="FIT_SCORE_THRESHOLD",
        description="Minimum score to classify a job as 'APTA' and trigger alerts",
    )

    def is_notion_configured(self) -> bool:
        """Check if Notion integration has required credentials."""
        return bool(self.notion_token and self.notion_database_id)

    def is_telegram_configured(self) -> bool:
        """Check if Telegram integration has required credentials."""
        return bool(self.telegram_bot_token and self.telegram_chat_id)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton instance of application settings."""
    return Settings()
