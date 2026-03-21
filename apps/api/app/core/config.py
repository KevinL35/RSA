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

    # TB-2：评论抓取 — http：POST REVIEW_PROVIDER_URL；apify：直连 Apify sync dataset
    review_provider_mode: str = "http"
    review_provider_url: str | None = None
    review_provider_api_key: str | None = None
    review_provider_timeout_seconds: float = 30.0
    review_fetch_max_retries: int = 3
    review_provider_mock: bool = False
    apify_token: str | None = None
    apify_actor_id: str | None = None
    apify_input_style: str = "asins"
    apify_max_reviews: int = 50
    apify_run_timeout_seconds: float = 240.0

    # Pangolin Amazon Review API（REVIEW_PROVIDER_MODE=pangolin）
    pangolin_token: str | None = None
    pangolin_base_url: str = "https://scrapeapi.pangolinfo.com"
    pangolin_amazon_url: str = "https://www.amazon.com"
    # Amazon 评论页约每页 10 条；10 页约 100 条（以 Pangolin 实际返回为准）
    pangolin_page_count: int = 10
    pangolin_filter_by_star: str = "all_stars"
    pangolin_sort_by: str = "recent"
    pangolin_parser_name: str = "amzReviewV2"
    pangolin_timeout_seconds: float = 180.0

    # TB-3：分析源（POST JSON：insight_task_id, platform, product_id, analysis_provider_id, reviews[]）
    analysis_provider_url: str | None = None
    analysis_provider_api_key: str | None = None
    analysis_provider_default_id: str = "default"
    analysis_provider_routes_json: str | None = None
    analysis_provider_timeout_seconds: float = 120.0
    analysis_max_retries: int = 2
    analysis_provider_mock: bool = False

    # TB-11：可选翻译代理（LibreTranslate 兼容：POST JSON q/source/target/format）
    translation_api_url: str | None = None
    translation_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
