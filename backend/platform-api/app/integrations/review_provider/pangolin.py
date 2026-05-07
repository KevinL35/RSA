"""
TB-2：Pangolin（Pangolinfo）Amazon Review API。
文档：https://docs.pangolinfo.com/cn-api-reference/amazonReviewAPI/amazonReviewAPI
"""

from __future__ import annotations

import json
import logging
import random
import time
from typing import Any

import httpx

from app.core.config import Settings

from .errors import ReviewProviderError
from .normalize import normalize_provider_item

log = logging.getLogger(__name__)

# 网关 / 源站过载时单次 pageCount 越大越容易触发 Cloudflare 504；在仍可降级时减半重试。
_GATEWAY_DEGRADE_STATUS = frozenset({500, 502, 503, 504})


def _is_transient_pangolin_error(exc: BaseException) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError, httpx.RemoteProtocolError)):
        return True
    msg = str(exc).lower()
    if "unexpected_eof_while_reading" in msg or "eof occurred in violation of protocol" in msg:
        return True
    if "handshake operation timed out" in msg or "connection reset" in msg:
        return True
    cause = getattr(exc, "__cause__", None)
    if cause is not None and cause is not exc:
        return _is_transient_pangolin_error(cause)
    return False


def _post_pangolin_json(
    *,
    url: str,
    body: dict[str, Any],
    headers: dict[str, str],
    timeout: httpx.Timeout,
    attempts: int,
) -> httpx.Response:
    last: BaseException | None = None
    total = max(1, attempts)
    for i in range(total):
        try:
            with httpx.Client(timeout=timeout, trust_env=False) as client:
                return client.post(url, json=body, headers=headers)
        except httpx.RequestError as e:
            last = e
            if i < total - 1 and _is_transient_pangolin_error(e):
                time.sleep(0.6 * (2**i) + random.uniform(0, 0.2))
                continue
            raise
    assert last is not None
    raise last


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
    initial_pages = max(1, min(int(settings.pangolin_page_count), cap))
    pages = initial_pages

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    timeout_sec = max(30.0, float(settings.pangolin_timeout_seconds))
    client_timeout = httpx.Timeout(timeout_sec, connect=30.0)
    parser_name = (settings.pangolin_parser_name or "amzReviewV2").strip()
    filter_star = (settings.pangolin_filter_by_star or "all_stars").strip()
    sort_by = (settings.pangolin_sort_by or "recent").strip()

    while True:
        body: dict[str, Any] = {
            "url": amazon_url,
            "bizContext": {
                "bizKey": "review",
                "pageCount": pages,
                "asin": asin,
                "filterByStar": filter_star,
                "sortBy": sort_by,
            },
            "format": "json",
            "parserName": parser_name,
        }
        try:
            resp = _post_pangolin_json(
                url=scrape_url,
                body=body,
                headers=headers,
                timeout=client_timeout,
                attempts=settings.review_fetch_max_retries,
            )
        except httpx.TimeoutException as e:
            if pages > 1:
                nxt = max(1, pages // 2)
                log.warning(
                    "pangolin read/connect timeout asin=%s pageCount %s -> %s",
                    asin,
                    pages,
                    nxt,
                )
                pages = nxt
                time.sleep(0.45 + random.uniform(0, 0.25))
                continue
            raise ReviewProviderError("REVIEW_PROVIDER_TIMEOUT", str(e) or "Pangolin 请求超时") from e
        except httpx.RequestError as e:
            if pages > 1 and _is_transient_pangolin_error(e):
                nxt = max(1, pages // 2)
                log.warning(
                    "pangolin request error asin=%s pageCount %s -> %s: %s",
                    asin,
                    pages,
                    nxt,
                    e,
                )
                pages = nxt
                time.sleep(0.45 + random.uniform(0, 0.25))
                continue
            code = "REVIEW_PROVIDER_TRANSIENT" if _is_transient_pangolin_error(e) else "REVIEW_PROVIDER_HTTP_ERROR"
            raise ReviewProviderError(
                code,
                str(e) or "连接 Pangolin 失败",
            ) from e

        if resp.status_code == 429:
            raise ReviewProviderError(
                "REVIEW_PROVIDER_TRANSIENT",
                f"Pangolin HTTP 429: {resp.text[:500]}",
            )
        if resp.status_code in _GATEWAY_DEGRADE_STATUS:
            if pages > 1:
                nxt = max(1, pages // 2)
                log.warning(
                    "pangolin HTTP %s asin=%s pageCount %s -> %s",
                    resp.status_code,
                    asin,
                    pages,
                    nxt,
                )
                pages = nxt
                time.sleep(0.55 + random.uniform(0, 0.25))
                continue
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

        if pages < initial_pages:
            log.info(
                "pangolin fetch ok asin=%s pageCount_used=%s (requested_max=%s) rows=%s",
                asin,
                pages,
                initial_pages,
                len(normalized),
            )
        return normalized
