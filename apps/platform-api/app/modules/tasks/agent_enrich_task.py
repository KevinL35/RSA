from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from supabase import Client

from app.core.config import get_settings
from app.integrations.agent_enrichment import AgentEnrichmentError, enrich_normalized_analyses
from app.modules.analysis_results.persist import replace_task_analysis


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_task_reviews_ordered(sb: Client, task_id: UUID) -> list[dict[str, Any]]:
    rv = (
        sb.table("reviews")
        .select("id,raw_text,title,rating,sku,reviewed_at,lang")
        .eq("insight_task_id", str(task_id))
        .order("created_at")
        .execute()
    )
    return list(rv.data or [])


def _load_normalized_from_db(sb: Client, task_id: UUID) -> list[dict[str, Any]]:
    ra = (
        sb.table("review_analysis")
        .select("*")
        .eq("insight_task_id", str(task_id))
        .execute()
    )
    analysis_rows = ra.data or []
    if not analysis_rows:
        return []

    dim_res = (
        sb.table("review_dimension_analysis")
        .select("*")
        .eq("insight_task_id", str(task_id))
        .execute()
    )
    by_ra: dict[str, list] = {}
    for d in dim_res.data or []:
        by_ra.setdefault(str(d["review_analysis_id"]), []).append(d)

    items: list[dict[str, Any]] = []
    for r in analysis_rows:
        ra_id = str(r["id"])
        rid = str(r["review_id"])
        dim_list = by_ra.get(ra_id, [])
        items.append(
            {
                "review_id": rid,
                "sentiment": {
                    "label": r["sentiment_label"],
                    "confidence": r.get("sentiment_confidence"),
                },
                "dimensions": [
                    {
                        "dimension": x["dimension"],
                        "keywords": x.get("keywords") or [],
                        "evidence_quote": x.get("evidence_quote"),
                        "highlight_spans": x.get("highlight_spans") or [],
                    }
                    for x in dim_list
                ],
            }
        )
    return items


def run_agent_enrich_for_task(sb: Client, task_id: UUID) -> dict:
    """
    任务已成功且已落库分析时，按环境变量对子集调用 Agent 并写回 TB-4（词典优先已完成后的补洞/抽检）。
    """
    res = (
        sb.table("insight_tasks")
        .select("*")
        .eq("id", str(task_id))
        .limit(1)
        .execute()
    )
    rows = res.data or []
    if not rows:
        raise HTTPException(status_code=404, detail="任务不存在")
    task = rows[0]
    if task["status"] != "success":
        raise HTTPException(
            status_code=400,
            detail="仅 success 任务可执行 agent-enrich，请先完成分析",
        )

    settings = get_settings()
    url = (settings.agent_enrichment_url or "").strip()
    if not url:
        raise HTTPException(
            status_code=503,
            detail="未配置 AGENT_ENRICHMENT_URL，无法执行智能 Agent 增强",
        )
    if not settings.agent_gap_fill_enabled and float(settings.agent_sample_fraction or 0) <= 0:
        raise HTTPException(
            status_code=400,
            detail="请启用 AGENT_GAP_FILL_ENABLED 或设置 AGENT_SAMPLE_FRACTION>0",
        )

    reviews = _load_task_reviews_ordered(sb, task_id)
    if not reviews:
        raise HTTPException(status_code=400, detail="任务下无评论数据")

    loaded = _load_normalized_from_db(sb, task_id)
    if not loaded:
        raise HTTPException(status_code=400, detail="任务无已落库分析结果，请先执行 analyze")

    by_r = {str(x["review_id"]): x for x in loaded}
    normalized: list[dict[str, Any]] = []
    for r in reviews:
        rid = r.get("id")
        if rid is None:
            continue
        rs = str(rid)
        normalized.append(
            by_r.get(rs)
            or {
                "review_id": rs,
                "sentiment": {"label": "neutral", "confidence": None},
                "dimensions": [],
            },
        )

    try:
        merged, stats = enrich_normalized_analyses(
            settings=settings,
            insight_task_id=str(task_id),
            platform=task["platform"],
            product_id=task["product_id"],
            dictionary_vertical_id=task.get("dictionary_vertical_id"),
            reviews=reviews,
            normalized=normalized,
        )
    except AgentEnrichmentError as e:
        raise HTTPException(
            status_code=502,
            detail=f"{e.code}: {e.message}",
        ) from e

    provider_id = task.get("analysis_provider_id") or "unknown"
    if isinstance(provider_id, str) and provider_id.strip():
        provider_used = provider_id.strip()
    else:
        provider_used = "unknown"

    try:
        replace_task_analysis(
            sb,
            insight_task_id=str(task_id),
            platform=task["platform"],
            product_id=task["product_id"],
            analysis_provider_id=provider_used,
            review_analyses=merged,
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Agent 增强结果落库失败：{e!s}") from e

    sb.table("insight_tasks").update({"updated_at": _utc_now_iso()}).eq("id", str(task_id)).execute()

    return {
        "insight_task_id": str(task_id),
        "agent_enrichment": stats,
        "analysis_provider_id": provider_used,
    }
