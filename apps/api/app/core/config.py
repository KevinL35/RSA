from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "RSA API"
    env: str = "dev"
    cors_origins: str = "http://localhost:5173,http://localhost:5174"

    supabase_url: str | None = None
    supabase_service_role_key: str | None = None

    # TB-2：评论抓取 API（POST JSON：platform, product_id；可选 Bearer）
    review_provider_url: str | None = None
    review_provider_api_key: str | None = None
    review_provider_timeout_seconds: float = 30.0
    review_fetch_max_retries: int = 3
    review_provider_mock: bool = False

    # TB-3：分析源（POST JSON：insight_task_id, platform, product_id, analysis_provider_id, reviews[]）
    analysis_provider_url: str | None = None
    analysis_provider_api_key: str | None = None
    analysis_provider_default_id: str = "default"
    analysis_provider_routes_json: str | None = None
    analysis_provider_timeout_seconds: float = 120.0
    analysis_max_retries: int = 2
    analysis_provider_mock: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
