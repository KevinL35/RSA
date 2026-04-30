"""
TB-2：Pangolin（Pangolinfo）Amazon Review API。
文档：https://docs.pangolinfo.com/cn-api-reference/amazonReviewAPI/amazonReviewAPI
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.core.config import Settings

from .errors import ReviewProviderError
from .normalize import normalize_provider_item


def _extract_result_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """解析 data.json[] 内嵌的 data.results。"""
    rows: list[dict[str, Any]] = []
    data = payload.get("data")
    if not isinstance(data, dict):
        return rows
    json_arr = data.get("json")
    if not isinstance(json_arr, list):
        return rows
    for block in json_arr:
        entry: Any = block
        if isinstance(block, str):
            try:
                entry = json.loads(block)
            except (json.JSONDecodeError, TypeError):
                continue
        if not isinstance(entry, dict):
            continue
        inner = entry.get("data")
        if not isinstance(inner, dict):
            continue
        results = inner.get("results")
        if isinstance(results, list):
            for r in results:
                if isinstance(r, dict):
                    rows.append(r)
    return rows


def _map_pangolin_review(r: dict[str, Any]) -> dict[str, Any] | None:
    text = r.get("content") or r.get("body") or r.get("text")
    if text is None or not str(text).strip():
        return None
    rid = r.get("reviewId") or r.get("review_id") or r.get("id")
    title = r.get("title")
    star = r.get("star")
    rating: float | None = None
    if star is not None:
        try:
            rating = float(str(star).replace(",", "."))
        except (TypeError, ValueError):
            pass
    reviewed = r.get("date")
    out: dict[str, Any] = {"raw_text": str(text).strip()}
    if rid is not None:
        out["external_review_id"] = str(rid)
    if title is not None and str(title).strip():
        out["title"] = str(title).strip()
    if rating is not None:
        out["rating"] = rating
    if reviewed is not None:
        out["reviewed_at"] = str(reviewed)
    for k in ("author", "authorId", "country", "reviewLink", "purchased", "vineVoice"):
        if k in r and r[k] is not None:
            out[k] = r[k]
    return out


def fetch_reviews_via_pangolin(
    platform: str,
    product_id: str,
    *,
    settings: Settings,
) -> list[dict[str, Any]]:
    token = (settings.pangolin_token or "").strip()
    if not token:
        raise ReviewProviderError(
            "REVIEW_PROVIDER_NOT_CONFIGURED",
            "REVIEW_PROVIDER_MODE=pangolin 时需配置 PANGOLIN_TOKEN（见 POST .../auth 返回的 data）",
        )
    pl = platform.strip().lower()
    if pl != "amazon":
        raise ReviewProviderError(
            "REVIEW_PROVIDER_HTTP_ERROR",
            f"Pangolin 评论接口当前仅支持 platform=amazon，收到 {platform!r}",
        )
    asin = product_id.strip()
    if not asin:
        raise ReviewProviderError("REVIEW_PROVIDER_HTTP_ERROR", "product_id 为空")

    base = (settings.pangolin_base_url or "https://scrapeapi.pangolinfo.com").rstrip("/")
    scrape_url = f"{base}/api/v1/scrape"
    amazon_url = (settings.pangolin_amazon_url or "https://www.amazon.com").strip()
    cap = max(1, int(settings.pangolin_page_count_max))
    page_count = max(1, min(int(settings.pangolin_page_count), cap))

    body: dict[str, Any] = {
        "url": amazon_url,
        "bizContext": {
            "bizKey": "review",
            "pageCount": page_count,
            "asin": asin,
            "filterByStar": (settings.pangolin_filter_by_star or "all_stars").strip(),
            "sortBy": (settings.pangolin_sort_by or "recent").strip(),
        },
        "format": "json",
        "parserName": (settings.pangolin_parser_name or "amzReviewV2").strip(),
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    timeout_sec = max(30.0, float(settings.pangolin_timeout_seconds))
    client_timeout = httpx.Timeout(timeout_sec, connect=30.0)

    try:
        with httpx.Client(timeout=client_timeout) as client:
            resp = client.post(scrape_url, json=body, headers=headers)
    except httpx.TimeoutException as e:
        raise ReviewProviderError("REVIEW_PROVIDER_TIMEOUT", str(e) or "Pangolin 请求超时") from e
    except httpx.RequestError as e:
        raise ReviewProviderError(
            "REVIEW_PROVIDER_HTTP_ERROR",
            str(e) or "连接 Pangolin 失败",
        ) from e

    if resp.status_code in (429, 500, 502, 503, 504):
        raise ReviewProviderError(
            "REVIEW_PROVIDER_TRANSIENT",
            f"Pangolin HTTP {resp.status_code}: {resp.text[:500]}",
        )
    if resp.status_code >= 400:
        raise ReviewProviderError(
            "REVIEW_PROVIDER_HTTP_ERROR",
            f"Pangolin HTTP {resp.status_code}: {resp.text[:800]}",
        )

    try:
        payload = resp.json()
    except ValueError as e:
        raise ReviewProviderError(
            "REVIEW_PROVIDER_PARSE_ERROR",
            f"Pangolin 响应非 JSON：{e!s}",
        ) from e

    if not isinstance(payload, dict):
        raise ReviewProviderError("REVIEW_PROVIDER_PARSE_ERROR", "Pangolin 响应应为 JSON 对象")

    api_code = payload.get("code")
    if api_code != 0:
        msg = payload.get("message") or str(api_code)
        raise ReviewProviderError(
            "REVIEW_PROVIDER_HTTP_ERROR",
            f"Pangolin 业务错误 code={api_code}: {msg}",
        )

    raw_reviews = _extract_result_rows(payload)
    normalized: list[dict[str, Any]] = []
    for r in raw_reviews:
        mapped = _map_pangolin_review(r)
        if not mapped:
            continue
        row = normalize_provider_item(mapped)
        if row:
            normalized.append(row)
    return normalized
