from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_PLATFORM_API_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_ENV_FILE = _PLATFORM_API_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_DEFAULT_ENV_FILE if _DEFAULT_ENV_FILE.is_file() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Platform API"
    env: str = "dev"
    cors_origins: str = "http://localhost:5173,http://localhost:5174"

    supabase_url: str | None = None
    supabase_service_role_key: str | None = None

    review_provider_mode: str = "http"
    review_provider_url: str | None = None
    review_provider_api_key: str | None = None
    review_provider_timeout_seconds: float = 30.0
    review_fetch_max_retries: int = 3
    review_provider_mock: bool = False

    pangolin_token: str | None = None
    pangolin_base_url: str = "https://scrapeapi.pangolinfo.com"
    pangolin_amazon_url: str = "https://www.amazon.com"
    pangolin_page_count: int = 10
    pangolin_page_count_max: int = 10
    pangolin_filter_by_star: str = "all_stars"
    pangolin_sort_by: str = "recent"
    pangolin_parser_name: str = "amzReviewV2"
    pangolin_timeout_seconds: float = 180.0
    pangolin_fetch_product_detail: bool = True
    pangolin_product_zipcode: str = "10041"
    pangolin_product_parser_name: str = "amzProductDetail"

    analysis_provider_url: str | None = None
    analysis_provider_api_key: str | None = None
    analysis_provider_default_id: str = "default"
    analysis_provider_routes_json: str | None = None
    analysis_provider_timeout_seconds: float = 120.0
    analysis_max_retries: int = 2
    analysis_provider_mock: bool = False

    deepseek_adapter_analyze_url: str = "http://127.0.0.1:9100/analyze"

    insight_summary_url: str = "http://127.0.0.1:9100/insight-summary"
    insight_summary_api_key: str | None = None
    insight_summary_timeout_seconds: float = 120.0
    insight_summary_auto_after_analyze: bool = True
    topic_discovery_auto_after_analyze: bool = False
    topic_discovery_auto_embedding_model: str = "ml/all-MiniLM-L6-v2"

    agent_enrichment_url: str | None = None
    deepseek_adapter_agent_enrich_url: str = "http://127.0.0.1:9100/agent-enrich"
    deepseek_adapter_dictionary_smart_merge_url: str = "http://127.0.0.1:9100/dictionary-smart-merge"
    agent_enrichment_api_key: str | None = None
    agent_enrichment_timeout_seconds: float = 120.0
    agent_enrichment_max_retries: int = 2
    agent_enrichment_batch_size: int = 50
    agent_gap_fill_enabled: bool = False
    agent_gap_fill_deferred: bool = False
    agent_sample_fraction: float = 0.0
    agent_sample_seed: int | None = None

    translation_api_url: str | None = None
    translation_api_key: str | None = None


def get_settings() -> Settings:
    """每次调用重新加载 .env / 环境变量，避免改 PANGOLIN_PAGE_COUNT 等后必须重启进程。"""
    return Settings()
