"""可选：在词典分析之后调用外部智能 Agent，对子集评论做六维补全/抽检（HTTP JSON）。

Agent 服务约定（与 TB-3 分析源响应对齐，便于复用同一解析器）：

- 请求：POST JSON，字段含 ``enrichment_mode``（``gap_fill`` | ``sample`` | ``mixed``）、
  ``insight_task_id``、``platform``、``product_id``、``dictionary_vertical_id``、
  ``reviews``（子集，结构与 TB-3 请求体中单条评论相同）。
- 响应：JSON，顶层含 ``reviews`` 数组；每项含 ``review_id``、可选 ``sentiment``、
  ``dimensions``（六维块，字段与 TB-3 归一化一致：dimension、keywords、evidence_quote、highlight_spans）。

平台侧已做词典分析后再调 Agent，故子集通常为「无词典命中」和/或抽检样本。
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.modules.dictionary.verticals import DEFAULT_VERTICAL_ID
from app.integrations.analysis_provider.normalize import build_canonical_response

from .merge import is_dictionary_gap, merge_gap_fill, merge_sample_keywords


class AgentEnrichmentError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def _review_payload_row(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": r.get("id"),
        "raw_text": r.get("raw_text"),
        "title": r.get("title"),
        "rating": r.get("rating"),
        "sku": r.get("sku"),
        "reviewed_at": r.get("reviewed_at"),
        "lang": r.get("lang"),
    }


def call_agent_enrichment_batch(
    *,
    url: str,
    api_key: str | None,
    timeout: float,
    max_retries: int,
    insight_task_id: str,
    platform: str,
    product_id: str,
    dictionary_vertical_id: str | None,
    enrichment_mode: str,
    reviews_subset: list[dict[str, Any]],
    review_ids_order: list[str],
) -> list[dict[str, Any]]:
    """
    POST Agent 服务；期望响应可被 build_canonical_response 解析（与 TB-3 分析源类似）。
    请求体含 enrichment_mode：gap_fill | sample | mixed。
    """
    if not reviews_subset:
        return []
    headers: dict[str, str] = {"Content-Type": "application/json", "Accept": "application/json"}
    key = (api_key or "").strip()
    if key:
        headers["Authorization"] = f"Bearer {key}"

    body: dict[str, Any] = {
        "enrichment_mode": enrichment_mode,
        "insight_task_id": insight_task_id,
        "platform": platform,
        "product_id": product_id,
        "dictionary_vertical_id": (dictionary_vertical_id or DEFAULT_VERTICAL_ID).strip() or DEFAULT_VERTICAL_ID,
        "reviews": [_review_payload_row(r) for r in reviews_subset],
    }

    attempts = max(1, max_retries)
    last_detail = ""
    for attempt in range(attempts):
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, json=body, headers=headers)
            if resp.status_code in (429, 500, 502, 503, 504):
                last_detail = f"HTTP {resp.status_code}: {resp.text[:500]}"
                raise AgentEnrichmentError("AGENT_ENRICHMENT_TRANSIENT", last_detail)
            if resp.status_code >= 400:
                raise AgentEnrichmentError(
                    "AGENT_ENRICHMENT_HTTP_ERROR",
                    f"HTTP {resp.status_code}: {resp.text[:800]}",
                )
            try:
                payload = resp.json()
            except ValueError as e:
                raise AgentEnrichmentError("AGENT_ENRICHMENT_PARSE_ERROR", f"响应非 JSON：{e!s}") from e
            normalized = build_canonical_response(payload, review_ids_order)
            return normalized
        except AgentEnrichmentError as e:
            if e.code == "AGENT_ENRICHMENT_TRANSIENT" and attempt < attempts - 1:
                time.sleep(0.5 * (2**attempt))
                continue
            raise
        except httpx.TimeoutException as e:
            last_detail = str(e)
            if attempt < attempts - 1:
                time.sleep(0.5 * (2**attempt))
                continue
            raise AgentEnrichmentError("AGENT_ENRICHMENT_TIMEOUT", last_detail or "请求超时") from e
        except httpx.RequestError as e:
            last_detail = str(e)
            if attempt < attempts - 1:
                time.sleep(0.5 * (2**attempt))
                continue
            raise AgentEnrichmentError("AGENT_ENRICHMENT_HTTP_ERROR", last_detail or "网络请求失败") from e

    raise AgentEnrichmentError("AGENT_ENRICHMENT_TRANSIENT", last_detail or "重试耗尽")


def enrich_normalized_analyses(
    *,
    settings: Settings | None = None,
    insight_task_id: str,
    platform: str,
    product_id: str,
    dictionary_vertical_id: str | None,
    reviews: list[dict[str, Any]],
    normalized: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    在词典已产出 normalized 后调用 Agent（若配置启用）。
    返回 (合并后的列表, 统计信息 dict)。
    """
    cfg = settings or get_settings()
    url = (cfg.agent_enrichment_url or "").strip()
    stats: dict[str, Any] = {
        "enabled": False,
        "gap_fill": False,
        "sample_fraction": 0.0,
        "gap_review_ids": [],
        "sample_review_ids": [],
        "batches": 0,
        "error": None,
    }

    if not url:
        return normalized, stats

    gap_on = cfg.agent_gap_fill_enabled
    frac = float(cfg.agent_sample_fraction or 0.0)
    if not gap_on and frac <= 0.0:
        return normalized, stats

    stats["enabled"] = True
    stats["gap_fill"] = gap_on
    stats["sample_fraction"] = frac

    by_id: dict[str, dict[str, Any]] = {str(x["review_id"]): x for x in normalized}
    gap_ids: list[str] = []
    if gap_on:
        for item in normalized:
            rid = str(item["review_id"])
            if is_dictionary_gap(item):
                gap_ids.append(rid)

    import random

    gap_set = set(gap_ids)
    non_gap = [str(x["review_id"]) for x in normalized if str(x["review_id"]) not in gap_set]
    sample_n = max(0, int(round(frac * len(non_gap)))) if frac > 0 and non_gap else 0
    sample_ids: list[str] = []
    if sample_n > 0:
        seed = cfg.agent_sample_seed
        rng = random.Random(int(seed)) if seed is not None else random.Random()
        sample_ids = rng.sample(non_gap, min(sample_n, len(non_gap)))

    target_ids = list(dict.fromkeys(gap_ids + sample_ids))
    stats["gap_review_ids"] = gap_ids
    stats["sample_review_ids"] = sample_ids

    if not target_ids:
        return normalized, stats

    reviews_by_id = {str(r["id"]): r for r in reviews if r.get("id") is not None}
    batch_size = max(1, min(200, int(cfg.agent_enrichment_batch_size or 50)))

    mode = "mixed"
    if gap_on and frac <= 0.0:
        mode = "gap_fill"
    elif not gap_on and frac > 0.0:
        mode = "sample"

    merged = {rid: dict(by_id[rid]) for rid in by_id}
    batch_count = 0
    for i in range(0, len(target_ids), batch_size):
        batch_ids = target_ids[i : i + batch_size]
        subset = [reviews_by_id[rid] for rid in batch_ids if rid in reviews_by_id]
        if len(subset) != len(batch_ids):
            continue
        batch_count += 1
        agent_items = call_agent_enrichment_batch(
            url=url,
            api_key=cfg.agent_enrichment_api_key,
            timeout=float(cfg.agent_enrichment_timeout_seconds),
            max_retries=int(cfg.agent_enrichment_max_retries),
            insight_task_id=insight_task_id,
            platform=platform,
            product_id=product_id,
            dictionary_vertical_id=dictionary_vertical_id,
            enrichment_mode=mode,
            reviews_subset=subset,
            review_ids_order=batch_ids,
        )
        agent_by_id = {str(x["review_id"]): x for x in agent_items}
        for rid in batch_ids:
            base = merged.get(rid)
            agent = agent_by_id.get(rid)
            if not base or not agent:
                continue
            if rid in gap_ids:
                merged[rid] = merge_gap_fill(base, agent)
            elif rid in sample_ids:
                merged[rid] = merge_sample_keywords(base, agent)

    stats["batches"] = batch_count
    out_list = [merged[str(x["review_id"])] for x in normalized]
    return out_list, stats


def agent_enrichment_configured(settings: Settings | None = None) -> bool:
    cfg = settings or get_settings()
    return bool((cfg.agent_enrichment_url or "").strip())
