from __future__ import annotations

import json

from app.core.config import Settings


def resolve_analysis_endpoint(
    settings: Settings,
    task_provider_id: str | None,
) -> tuple[str, str]:
    """
    返回 (生效的 analysis_provider_id, 请求 URL)。
    规则：任务字段优先，否则用 ANALYSIS_PROVIDER_DEFAULT_ID；
    URL 优先查 ANALYSIS_PROVIDER_ROUTES_JSON[id]，否则回退 ANALYSIS_PROVIDER_URL。
    """
    default_id = (settings.analysis_provider_default_id or "default").strip() or "default"
    raw = (task_provider_id or "").strip()
    effective = raw if raw else default_id

    routes: dict[str, str] = {}
    if settings.analysis_provider_routes_json:
        try:
            parsed = json.loads(settings.analysis_provider_routes_json)
            if isinstance(parsed, dict):
                routes = {str(k): str(v).strip() for k, v in parsed.items() if str(v).strip()}
        except json.JSONDecodeError:
            routes = {}

    url = routes.get(effective) if routes else None
    if not url:
        url = (settings.analysis_provider_url or "").strip()

    if not url:
        raise ValueError(
            "未配置分析源 URL：请设置 ANALYSIS_PROVIDER_URL，或在 ANALYSIS_PROVIDER_ROUTES_JSON 中为 "
            f"{effective!r} 配置端点（也可用 ANALYSIS_PROVIDER_MOCK=true 联调）"
        )

    return effective, url
