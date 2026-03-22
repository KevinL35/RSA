from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 勿依赖进程 cwd：从仓库根 / 其它目录启动 uvicorn 时仍能读到 apps/platform-api/.env
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

    # TB-2：评论抓取 — http：POST REVIEW_PROVIDER_URL；pangolin：Pangolinfo
    review_provider_mode: str = "http"
    review_provider_url: str | None = None
    review_provider_api_key: str | None = None
    review_provider_timeout_seconds: float = 30.0
    review_fetch_max_retries: int = 3
    review_provider_mock: bool = False

    # Pangolin Amazon Review API（REVIEW_PROVIDER_MODE=pangolin）
    pangolin_token: str | None = None
    pangolin_base_url: str = "https://scrapeapi.pangolinfo.com"
    pangolin_amazon_url: str = "https://www.amazon.com"
    # 抓取页数：请在 apps/platform-api/.env 设 PANGOLIN_PAGE_COUNT（环境变量优先于下列默认值）
    pangolin_page_count: int = 10
    # 单请求 pageCount 上限：请在 .env 设 PANGOLIN_PAGE_COUNT_MAX；与 pangolin.py 中 min 一致
    pangolin_page_count_max: int = 100
    pangolin_filter_by_star: str = "all_stars"
    pangolin_sort_by: str = "recent"
    pangolin_parser_name: str = "amzReviewV2"
    pangolin_timeout_seconds: float = 180.0
    # 拉评时额外调 amzProductDetail（1 积点/次）；失败不阻断评论抓取
    pangolin_fetch_product_detail: bool = True
    pangolin_product_zipcode: str = "10041"
    pangolin_product_parser_name: str = "amzProductDetail"

    # TB-3：分析源（POST JSON：insight_task_id, platform, product_id, analysis_provider_id, reviews[]）
    analysis_provider_url: str | None = None
    analysis_provider_api_key: str | None = None
    analysis_provider_default_id: str = "default"
    analysis_provider_routes_json: str | None = None
    analysis_provider_timeout_seconds: float = 120.0
    analysis_max_retries: int = 2
    analysis_provider_mock: bool = False

    # 前端任务 analysis_provider_id=deepseek_chat 时，在未配置 ROUTES / 默认 URL 下的回退地址
    deepseek_adapter_analyze_url: str = "http://127.0.0.1:9100/analyze"

    # 可选：词典分析后的智能 Agent 增强（补洞 / 抽检）；见 agent_enrichment 模块
    agent_enrichment_url: str | None = None
    agent_enrichment_api_key: str | None = None
    agent_enrichment_timeout_seconds: float = 120.0
    agent_enrichment_max_retries: int = 2
    agent_enrichment_batch_size: int = 50
    # 为「词典无命中」的评论调用 Agent 补六维
    agent_gap_fill_enabled: bool = False
    # True：主分析不调 Agent，改由 POST .../agent-enrich
    agent_gap_fill_deferred: bool = False
    # 0~1：对已有词典命中的评论按比例抽检并合并 Agent 关键词
    agent_sample_fraction: float = 0.0
    # 固定种子便于复现抽检子集；None 为随机
    agent_sample_seed: int | None = None

    # TB-11：可选翻译代理（LibreTranslate 兼容：POST JSON q/source/target/format）
    translation_api_url: str | None = None
    translation_api_key: str | None = None


def get_settings() -> Settings:
    """每次调用重新加载 .env / 环境变量，避免改 PANGOLIN_PAGE_COUNT 等后必须重启进程。"""
    return Settings()
