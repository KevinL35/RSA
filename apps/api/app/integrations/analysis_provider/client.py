from __future__ import annotations

import time
from typing import Any

import httpx

from app.core.config import Settings, get_settings

from .normalize import build_canonical_response
from .resolve import effective_analysis_provider_id, resolve_analysis_endpoint


class AnalysisProviderError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def _mock_payload(
    effective_provider_id: str,
    reviews: list[dict[str, Any]],
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for r in reviews:
        rid = str(r.get("id", ""))
        raw = str(r.get("raw_text", ""))[:120]
        items.append(
            {
                "review_id": rid,
                "sentiment": {"label": "positive", "confidence": 0.91},
                "dimensions": [
                    {
                        "dimension": "pros",
                        "keywords": ["mock", "tb3"],
                        "evidence_quote": raw or "[mock]",
                        "highlight_spans": [],
                    }
                ],
                "_mock": True,
                "_analysis_provider_id": effective_provider_id,
            }
        )
    return {"reviews": items}


def analyze_reviews(
    *,
    insight_task_id: str,
    platform: str,
    product_id: str,
    task_analysis_provider_id: str | None,
    reviews: list[dict[str, Any]],
    dictionary_vertical_id: str | None = None,
    settings: Settings | None = None,
) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
    """
    调用分析源，返回 (生效的 provider_id, 规范化后的逐条分析列表, 原始响应 dict)。
    """
    cfg = settings or get_settings()
    if not reviews:
        raise AnalysisProviderError("ANALYSIS_INPUT_EMPTY", "没有可分析的评论行")

    review_ids = [str(r["id"]) for r in reviews if r.get("id") is not None]
    if len(review_ids) != len(reviews):
        raise AnalysisProviderError("ANALYSIS_INPUT_INVALID", "评论行缺少 id")

    effective_id = effective_analysis_provider_id(cfg, task_analysis_provider_id)

    dvid = (dictionary_vertical_id or "general").strip() or "general"

    if cfg.analysis_provider_mock:
        raw = _mock_payload(effective_id, reviews)
        normalized = build_canonical_response(raw["reviews"], review_ids)
        return effective_id, normalized, raw

    try:
        _, url = resolve_analysis_endpoint(cfg, task_analysis_provider_id)
    except ValueError as e:
        raise AnalysisProviderError("ANALYSIS_PROVIDER_NOT_CONFIGURED", str(e)) from e

    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    key = (cfg.analysis_provider_api_key or "").strip()
    if key:
        headers["Authorization"] = f"Bearer {key}"

    body: dict[str, Any] = {
        "insight_task_id": insight_task_id,
        "platform": platform,
        "product_id": product_id,
        "analysis_provider_id": effective_id,
        "dictionary_vertical_id": dvid,
        "reviews": [
            {
                "id": r.get("id"),
                "raw_text": r.get("raw_text"),
                "title": r.get("title"),
                "rating": r.get("rating"),
                "sku": r.get("sku"),
                "reviewed_at": r.get("reviewed_at"),
                "lang": r.get("lang"),
            }
            for r in reviews
        ],
    }

    attempts = max(1, cfg.analysis_max_retries)
    timeout = cfg.analysis_provider_timeout_seconds
    last_detail = ""

    for attempt in range(attempts):
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, json=body, headers=headers)
            if resp.status_code in (429, 500, 502, 503, 504):
                last_detail = f"HTTP {resp.status_code}: {resp.text[:500]}"
                raise AnalysisProviderError("ANALYSIS_PROVIDER_TRANSIENT", last_detail)
            if resp.status_code >= 400:
                raise AnalysisProviderError(
                    "ANALYSIS_PROVIDER_HTTP_ERROR",
                    f"HTTP {resp.status_code}: {resp.text[:800]}",
                )
            try:
                payload = resp.json()
            except ValueError as e:
                raise AnalysisProviderError(
                    "ANALYSIS_PROVIDER_PARSE_ERROR",
                    f"响应非 JSON：{e!s}",
                ) from e
            if not isinstance(payload, (dict, list)):
                raise AnalysisProviderError(
                    "ANALYSIS_PROVIDER_PARSE_ERROR",
                    "响应 JSON 顶层须为 object 或 array",
                )
            normalized = build_canonical_response(payload, review_ids)
            return effective_id, normalized, payload if isinstance(payload, dict) else {"_array": payload}
        except AnalysisProviderError as e:
            if e.code == "ANALYSIS_PROVIDER_TRANSIENT" and attempt < attempts - 1:
                time.sleep(0.5 * (2**attempt))
                continue
            raise
        except httpx.TimeoutException as e:
            last_detail = str(e)
            if attempt < attempts - 1:
                time.sleep(0.5 * (2**attempt))
                continue
            raise AnalysisProviderError(
                "ANALYSIS_PROVIDER_TIMEOUT",
                last_detail or "请求超时",
            ) from e
        except httpx.RequestError as e:
            last_detail = str(e)
            if attempt < attempts - 1:
                time.sleep(0.5 * (2**attempt))
                continue
            raise AnalysisProviderError(
                "ANALYSIS_PROVIDER_HTTP_ERROR",
                last_detail or "网络请求失败",
            ) from e

    raise AnalysisProviderError("ANALYSIS_PROVIDER_TRANSIENT", last_detail or "重试耗尽")
