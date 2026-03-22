"""TB-2：内置 Apify run-sync-get-dataset-items，与薄代理逻辑对齐。"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from app.core.config import Settings

from .errors import ReviewProviderError
from .normalize import normalize_provider_item


def _build_apify_input(platform: str, product_id: str, cfg: Settings) -> dict[str, Any]:
    pl = platform.strip().lower()
    if pl != "amazon":
        raise ReviewProviderError(
            "REVIEW_PROVIDER_HTTP_ERROR",
            f"内置 Apify 当前仅支持 platform=amazon，收到 {platform!r}",
        )
    asin = product_id.strip()
    if not asin:
        raise ReviewProviderError(
            "REVIEW_PROVIDER_HTTP_ERROR",
            "product_id 为空",
        )
    style = (cfg.apify_input_style or "asins").strip().lower()
    n = max(1, min(cfg.apify_max_reviews, 500))
    if style == "producturls":
        return {
            "productUrls": [{"url": f"https://www.amazon.com/dp/{asin}"}],
            "maxReviews": n,
        }
    if style != "asins":
        raise ReviewProviderError(
            "REVIEW_PROVIDER_NOT_CONFIGURED",
            "APIFY_INPUT_STYLE 须为 asins 或 productUrls",
        )
    return {"asins": [asin], "maxReviews": n}


def _map_apify_row(item: dict[str, Any]) -> dict[str, Any] | None:
    for key in (
        "reviewText",
        "text",
        "reviewDescription",
        "reviewBody",
        "body",
        "review",
        "content",
    ):
        v = item.get(key)
        if v is not None and str(v).strip():
            raw = str(v).strip()
            break
    else:
        return None
    ext = item.get("id") or item.get("reviewId") or item.get("review_id")
    rating = item.get("rating") or item.get("stars") or item.get("reviewRating")
    title = item.get("title") or item.get("reviewTitle")
    reviewed = item.get("date") or item.get("reviewDate") or item.get("created_at")
    out: dict[str, Any] = {"raw_text": raw}
    if ext is not None:
        out["external_review_id"] = str(ext)
    if title is not None and str(title).strip():
        out["title"] = str(title).strip()
    if reviewed is not None:
        out["reviewed_at"] = str(reviewed)
    if rating is not None:
        try:
            out["rating"] = float(rating)
        except (TypeError, ValueError):
            pass
    return out


def fetch_reviews_via_apify(
    platform: str,
    product_id: str,
    *,
    settings: Settings,
) -> list[dict[str, Any]]:
    token = (settings.apify_token or "").strip()
    actor = (settings.apify_actor_id or "").strip()
    if not token or not actor:
        raise ReviewProviderError(
            "REVIEW_PROVIDER_NOT_CONFIGURED",
            "REVIEW_PROVIDER_MODE=apify 时需配置 APIFY_TOKEN 与 APIFY_ACTOR_ID",
        )

    apify_input = _build_apify_input(platform, product_id, settings)
    timeout_sec = max(1.0, min(float(settings.apify_run_timeout_seconds), 300.0))
    actor_path = quote(actor, safe="")
    url = f"https://api.apify.com/v2/acts/{actor_path}/run-sync-get-dataset-items"
    headers = {"Authorization": f"Bearer {token}"}
    params: dict[str, Any] = {"timeout": timeout_sec}
    client_timeout = httpx.Timeout(timeout_sec + 60.0, connect=30.0)

    try:
        with httpx.Client(timeout=client_timeout) as client:
            resp = client.post(url, params=params, json=apify_input, headers=headers)
    except httpx.TimeoutException as e:
        raise ReviewProviderError("REVIEW_PROVIDER_TIMEOUT", str(e) or "Apify 请求超时") from e
    except httpx.RequestError as e:
        raise ReviewProviderError(
            "REVIEW_PROVIDER_HTTP_ERROR",
            str(e) or "连接 Apify 失败",
        ) from e

    if resp.status_code in (429, 500, 502, 503, 504):
        raise ReviewProviderError(
            "REVIEW_PROVIDER_TRANSIENT",
            f"Apify HTTP {resp.status_code}: {resp.text[:500]}",
        )
    if resp.status_code == 408:
        raise ReviewProviderError(
            "REVIEW_PROVIDER_TRANSIENT",
            "Apify run 超时（408），可增大 APIFY_RUN_TIMEOUT_SECONDS 或减少 APIFY_MAX_REVIEWS",
        )
    if resp.status_code not in (200, 201):
        raise ReviewProviderError(
            "REVIEW_PROVIDER_HTTP_ERROR",
            f"Apify HTTP {resp.status_code}: {resp.text[:800]}",
        )

    try:
        payload = resp.json()
    except ValueError as e:
        raise ReviewProviderError(
            "REVIEW_PROVIDER_PARSE_ERROR",
            f"Apify 响应非 JSON：{e!s}",
        ) from e

    if not isinstance(payload, list):
        raise ReviewProviderError(
            "REVIEW_PROVIDER_PARSE_ERROR",
            "Apify 同步接口应返回 JSON 数组",
        )

    normalized: list[dict[str, Any]] = []
    for row in payload:
        if not isinstance(row, dict):
            continue
        mapped = _map_apify_row(row)
        if not mapped:
            continue
        item = normalize_provider_item(mapped)
        if item:
            normalized.append(item)
    return normalized
