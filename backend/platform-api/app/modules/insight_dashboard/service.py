from __future__ import annotations

from collections import Counter
from typing import Any
from uuid import UUID

from supabase import Client
from app.modules.dictionary.verticals import DEFAULT_VERTICAL_ID


def _count_reviews_for_task(sb: Client, task_id: UUID) -> int:
    """任务下已入库评论条数。"""
    try:
        res = (
            sb.table("reviews")
            .select("id", count="exact")
            .eq("insight_task_id", str(task_id))
            .limit(1)
            .execute()
        )
        c = res.count
        return c if isinstance(c, int) else 0
    except Exception:  # noqa: BLE001
        return 0


def _review_volume_by_reviewed_date(sb: Client, task_id: UUID) -> list[dict[str, Any]]:
    """按评论 reviewed_at 的 UTC 日期聚合条数，供前端时间趋势图。"""
    rv = (
        sb.table("reviews")
        .select("reviewed_at")
        .eq("insight_task_id", str(task_id))
        .execute()
    )
    by_day: Counter[str] = Counter()
    for row in rv.data or []:
        raw = row.get("reviewed_at")
        if raw is None:
            continue
        s = str(raw)
        if len(s) >= 10 and s[4] == "-" and s[7] == "-":
            by_day[s[:10]] += 1
    return [{"date": d, "count": by_day[d]} for d in sorted(by_day.keys())]

_DIMS = frozenset(
    {
        "pros",
        "cons",
        "return_reasons",
        "purchase_motivation",
        "user_expectation",
        "usage_scenario",
    }
)


def build_insight_dashboard(
    sb: Client,
    task_id: UUID,
    *,
    evidence_limit: int = 50,
    evidence_offset: int = 0,
    evidence_dimension: str | None = None,
) -> dict[str, Any]:
    """聚合单任务的维度计数、关键词排行、证据分页列表；非 success 时返回明确 empty_state。"""
    tr = (
        sb.table("insight_tasks")
        .select("*")
        .eq("id", str(task_id))
        .limit(1)
        .execute()
    )
    trows = tr.data or []
    if not trows:
        return {"_not_found": True}
    task = trows[0]
    status = task["status"]
    review_total_count = _count_reviews_for_task(sb, task_id)

    base = {
        "insight_task_id": str(task_id),
        "platform": task["platform"],
        "product_id": task["product_id"],
        "task_status": status,
        "analysis_provider_id": task.get("analysis_provider_id"),
        "analyzed_at": task.get("updated_at"),
        "product_snapshot": task.get("product_snapshot"),
        "dictionary_vertical_id": task.get("dictionary_vertical_id") or DEFAULT_VERTICAL_ID,
        "review_total_count": review_total_count,
        "matched_review_count": 0,
    }

    empty_template = {
        **base,
        "empty_state": None,
        "dimension_counts": {},
        "pain_ranking": [],
        "evidence": {"items": [], "total": 0, "limit": evidence_limit, "offset": evidence_offset},
        "review_timeseries": [],
        "ai_summary": task.get("ai_summary"),
    }

    if status != "success":
        empty_template["empty_state"] = {
            "code": "TASK_NOT_READY",
            "message": "任务尚未完成分析，无法生成洞察看板",
            "hint": "请等待状态为 success，或先执行 fetch-reviews 与 analyze",
        }
        return empty_template

    dim_res = (
        sb.table("review_dimension_analysis")
        .select("*")
        .eq("insight_task_id", str(task_id))
        .execute()
    )
    hits_all: list[dict[str, Any]] = [h for h in (dim_res.data or []) if isinstance(h, dict)]
    matched_review_count = len(
        {
            str(h["review_id"])
            for h in hits_all
            if h.get("review_id") is not None and str(h.get("review_id", "")).strip()
        }
    )
    hits: list[dict[str, Any]] = list(hits_all)

    if not hits_all:
        empty_template["empty_state"] = {
            "code": "NO_ANALYSIS_DATA",
            "message": "任务已成功，但未找到维度命中数据",
            "hint": "可能分析源未返回六维结果",
        }
        empty_template["review_timeseries"] = _review_volume_by_reviewed_date(sb, task_id)
        return empty_template

    if evidence_dimension:
        ed = evidence_dimension.strip()
        if ed not in _DIMS:
            return {"_bad_dimension": ed}
        hits = [h for h in hits if h.get("dimension") == ed]

    dimension_counts: Counter[str] = Counter()
    kw_counter: Counter[str] = Counter()
    kw_dims: dict[str, set[str]] = {}

    for h in hits:
        d = h.get("dimension")
        if isinstance(d, str) and d in _DIMS:
            dimension_counts[d] += 1
        kws = h.get("keywords") or []
        if not isinstance(kws, list):
            continue
        for raw_kw in kws:
            if raw_kw is None:
                continue
            kw = str(raw_kw).strip().lower()
            if not kw:
                continue
            kw_counter[kw] += 1
            kw_dims.setdefault(kw, set()).add(str(d) if d else "")

    pain_ranking = [
        {
            "keyword": kw,
            "count": c,
            "dimensions": sorted(kw_dims.get(kw, set()) - {""}),
        }
        for kw, c in kw_counter.most_common(80)
    ]

    hits_sorted = sorted(
        hits,
        key=lambda x: (x.get("created_at") or "", str(x.get("id", ""))),
    )
    total_evidence = len(hits_sorted)
    page = hits_sorted[evidence_offset : evidence_offset + evidence_limit]

    rids = list({str(h["review_id"]) for h in page if h.get("review_id")})
    review_map: dict[str, dict] = {}
    if rids:
        rv = sb.table("reviews").select("id,raw_text,title,rating,sku,reviewed_at").in_("id", rids).execute()
        for row in rv.data or []:
            review_map[str(row["id"])] = row

    evidence_items = []
    for h in page:
        rid = str(h.get("review_id", ""))
        evidence_items.append(
            {
                "id": h.get("id"),
                "dimension": h.get("dimension"),
                "keywords": h.get("keywords") or [],
                "evidence_quote": h.get("evidence_quote"),
                "highlight_spans": h.get("highlight_spans") or [],
                "review_id": rid,
                "insight_task_id": h.get("insight_task_id"),
                "review": review_map.get(rid),
            }
        )

    return {
        **base,
        "empty_state": None,
        "matched_review_count": matched_review_count,
        "dimension_counts": dict(sorted(dimension_counts.items())),
        "pain_ranking": pain_ranking,
        "evidence": {
            "items": evidence_items,
            "total": total_evidence,
            "limit": evidence_limit,
            "offset": evidence_offset,
        },
        "review_timeseries": _review_volume_by_reviewed_date(sb, task_id),
        "ai_summary": task.get("ai_summary"),
    }
