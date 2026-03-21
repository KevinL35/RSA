from __future__ import annotations

from typing import Any

from supabase import Client

_ALLOWED_DIMS = frozenset(
    {
        "pros",
        "cons",
        "return_reasons",
        "purchase_motivation",
        "user_expectation",
        "usage_scenario",
    }
)


def replace_task_analysis(
    sb: Client,
    *,
    insight_task_id: str,
    platform: str,
    product_id: str,
    analysis_provider_id: str,
    review_analyses: list[dict[str, Any]],
) -> None:
    """删除该任务既有分析行后，按 TB-3 规范化结构重写入库。"""
    sb.table("review_analysis").delete().eq("insight_task_id", insight_task_id).execute()

    if not review_analyses:
        return

    ra_rows: list[dict[str, Any]] = []
    for item in review_analyses:
        sent = item.get("sentiment") or {}
        label = sent.get("label") or "neutral"
        if label not in ("negative", "neutral", "positive"):
            label = "neutral"
        ra_rows.append(
            {
                "insight_task_id": insight_task_id,
                "review_id": item["review_id"],
                "platform": platform,
                "product_id": product_id,
                "sentiment_label": label,
                "sentiment_confidence": sent.get("confidence"),
                "analysis_provider_id": analysis_provider_id,
            }
        )

    ins = sb.table("review_analysis").insert(ra_rows).execute()
    inserted = ins.data or []
    if len(inserted) != len(ra_rows):
        raise RuntimeError("review_analysis 插入数量与预期不符")

    id_by_review = {str(row["review_id"]): row["id"] for row in inserted}

    dim_rows: list[dict[str, Any]] = []
    for item in review_analyses:
        rid = str(item["review_id"])
        ra_id = id_by_review.get(rid)
        if not ra_id:
            continue
        for d in item.get("dimensions") or []:
            if not isinstance(d, dict):
                continue
            dim = d.get("dimension")
            if not dim or str(dim) not in _ALLOWED_DIMS:
                continue
            kws = d.get("keywords") or []
            if not isinstance(kws, list):
                kws = []
            spans = d.get("highlight_spans") or []
            if not isinstance(spans, list):
                spans = []
            dim_rows.append(
                {
                    "review_analysis_id": ra_id,
                    "insight_task_id": insight_task_id,
                    "review_id": rid,
                    "platform": platform,
                    "product_id": product_id,
                    "dimension": dim,
                    "keywords": [str(x) for x in kws if x is not None and str(x).strip()],
                    "evidence_quote": d.get("evidence_quote"),
                    "highlight_spans": spans,
                }
            )

    if dim_rows:
        sb.table("review_dimension_analysis").insert(dim_rows).execute()
