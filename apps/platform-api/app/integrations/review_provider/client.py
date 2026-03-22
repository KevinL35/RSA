from __future__ import annotations

import time
from typing import Any

import httpx

from app.core.config import Settings, get_settings

from .errors import ReviewProviderError
from .normalize import extract_review_list, normalize_provider_item


MOCK_REVIEW_COUNT = 100


def _mock_payload(platform: str, product_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i in range(1, MOCK_REVIEW_COUNT + 1):
        rows.append(
            {
                "external_review_id": f"mock-{i}",
                "raw_text": f"[mock #{i}] Sample review for {platform} / {product_id}. "
                f"Quality and delivery experience vary; this row is for pipeline testing.",
                "title": f"Mock title {i}",
                "rating": float(3 + (i % 3)),
                "lang": "en",
            }
        )
    return rows


def fetch_reviews_normalized(
    platform: str,
    product_id: str,
    *,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    """
    调用配置的评论抓取 API，返回已规范化的行字典列表（不含 task 维度字段）。
    含 HTTP 重试（429、5xx、连接/超时类错误）。
    """
    cfg = settings or get_settings()
    if cfg.review_provider_mock:
        out: list[dict[str, Any]] = []
        for x in _mock_payload(platform, product_id):
            row = normalize_provider_item(x)
            if row:
                out.append(row)
        return out

    mode = (cfg.review_provider_mode or "http").strip().lower()
    if mode == "apify":
        from .apify import fetch_reviews_via_apify

        attempts = max(1, cfg.review_fetch_max_retries)
        for attempt in range(attempts):
            try:
                return fetch_reviews_via_apify(platform, product_id, settings=cfg)
            except ReviewProviderError as e:
                if e.code == "REVIEW_PROVIDER_TRANSIENT" and attempt < attempts - 1:
                    time.sleep(0.4 * (2**attempt))
                    continue
                raise

    if mode == "pangolin":
        from .pangolin import fetch_reviews_via_pangolin

        attempts = max(1, cfg.review_fetch_max_retries)
        for attempt in range(attempts):
            try:
                return fetch_reviews_via_pangolin(platform, product_id, settings=cfg)
            except ReviewProviderError as e:
                if e.code == "REVIEW_PROVIDER_TRANSIENT" and attempt < attempts - 1:
                    time.sleep(0.4 * (2**attempt))
                    continue
                raise

    url = (cfg.review_provider_url or "").strip()
    if not url:
        raise ReviewProviderError(
            "REVIEW_PROVIDER_NOT_CONFIGURED",
            "未配置 REVIEW_PROVIDER_URL，或改用 REVIEW_PROVIDER_MODE=apify|pangolin 并配置对应变量；联调可设 REVIEW_PROVIDER_MOCK=true",
        )

    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    key = (cfg.review_provider_api_key or "").strip()
    if key:
        headers["Authorization"] = f"Bearer {key}"

    body = {"platform": platform, "product_id": product_id}
    attempts = max(1, cfg.review_fetch_max_retries)
    timeout = cfg.review_provider_timeout_seconds
    last_detail = ""

    for attempt in range(attempts):
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, json=body, headers=headers)
            if resp.status_code in (429, 500, 502, 503, 504):
                last_detail = f"HTTP {resp.status_code}: {resp.text[:500]}"
                raise ReviewProviderError("REVIEW_PROVIDER_TRANSIENT", last_detail)
            if resp.status_code >= 400:
                raise ReviewProviderError(
                    "REVIEW_PROVIDER_HTTP_ERROR",
                    f"HTTP {resp.status_code}: {resp.text[:800]}",
                )
            try:
                payload = resp.json()
            except ValueError as e:
                raise ReviewProviderError(
                    "REVIEW_PROVIDER_PARSE_ERROR",
                    f"响应非 JSON：{e!s}",
                ) from e
            raw_list = extract_review_list(payload)
            normalized: list[dict[str, Any]] = []
            for item in raw_list:
                row = normalize_provider_item(item)
                if row:
                    normalized.append(row)
            return normalized
        except ReviewProviderError as e:
            if e.code == "REVIEW_PROVIDER_TRANSIENT" and attempt < attempts - 1:
                time.sleep(0.4 * (2**attempt))
                continue
            raise
        except httpx.TimeoutException as e:
            last_detail = str(e)
            if attempt < attempts - 1:
                time.sleep(0.4 * (2**attempt))
                continue
            raise ReviewProviderError(
                "REVIEW_PROVIDER_TIMEOUT",
                last_detail or "请求超时",
            ) from e
        except httpx.RequestError as e:
            last_detail = str(e)
            if attempt < attempts - 1:
                time.sleep(0.4 * (2**attempt))
                continue
            raise ReviewProviderError(
                "REVIEW_PROVIDER_HTTP_ERROR",
                last_detail or "网络请求失败",
            ) from e
