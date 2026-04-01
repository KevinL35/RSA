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

_ALLOWED_DIMS_BY_SENTIMENT: dict[str, frozenset[str]] = {
    "positive": frozenset({"pros", "purchase_motivation", "usage_scenario"}),
    "negative": frozenset({"cons", "return_reasons", "user_expectation"}),
}


def _sentiment_allow_dimension(sentiment_label: str, dimension: str) -> bool:
    if sentiment_label == "neutral":
        return True
    allowed = _ALLOWED_DIMS_BY_SENTIMENT.get(sentiment_label)
    if allowed is None:
        return False
    return dimension in allowed


def replace_task_analysis(
    sb: Client,
    *,
    insight_task_id: str,
    platform: str,
    product_id: str,
    analysis_provider_id: str,
    review_analyses: list[dict[str, Any]],
) -> None:
    """删除该任务既有分析行后，按 TB-3 规范化结构重写入库。

    同时维护：
    - 三分类临时表（positive/neutral/negative）
    - 三分类总表中的六维匹配状态（dimension_match_status）
    - 三分类未命中总表（positive/neutral/negative unmatched）
    - 兼容未命中池 review_dimension_unmatched（主题挖掘补洞）
    """
    sb.table("review_analysis").delete().eq("insight_task_id", insight_task_id).execute()

    if not review_analyses:
        return

    has_dim_hit_by_review: dict[str, bool] = {}
    sent_label_by_review: dict[str, str] = {}
    for item in review_analyses:
        rid = str(item["review_id"])
        sent = item.get("sentiment") or {}
        label = sent.get("label") or "neutral"
        if label not in ("negative", "neutral", "positive"):
            label = "neutral"
        sent_label_by_review[rid] = label
        has_hit = False
        for d in item.get("dimensions") or []:
            if not isinstance(d, dict):
                continue
            dim = d.get("dimension")
            if not dim or str(dim) not in _ALLOWED_DIMS:
                continue
            if _sentiment_allow_dimension(label, str(dim)):
                has_hit = True
                break
        has_dim_hit_by_review[rid] = has_hit

    ra_rows: list[dict[str, Any]] = []
    for item in review_analyses:
        rid = str(item["review_id"])
        sent = item.get("sentiment") or {}
        label = sent_label_by_review.get(rid, "neutral")
        ra_rows.append(
            {
                "insight_task_id": insight_task_id,
                "review_id": rid,
                "platform": platform,
                "product_id": product_id,
                "sentiment_label": label,
                "sentiment_confidence": sent.get("confidence"),
                "analysis_provider_id": analysis_provider_id,
                "dimension_match_status": "matched" if has_dim_hit_by_review.get(rid, False) else "unmatched",
            }
        )

    ins = sb.table("review_analysis").insert(ra_rows).execute()
    inserted = ins.data or []
    if len(inserted) != len(ra_rows):
        raise RuntimeError("review_analysis 插入数量与预期不符")

    id_by_review = {str(row["review_id"]): row["id"] for row in inserted}

    dim_rows: list[dict[str, Any]] = []
    unmatched_rows: list[dict[str, Any]] = []
    pos_unmatched_rows: list[dict[str, Any]] = []
    neu_unmatched_rows: list[dict[str, Any]] = []
    neg_unmatched_rows: list[dict[str, Any]] = []
    pos_tmp_rows: list[dict[str, Any]] = []
    neu_tmp_rows: list[dict[str, Any]] = []
    neg_tmp_rows: list[dict[str, Any]] = []
    for item in review_analyses:
        rid = str(item["review_id"])
        ra_id = id_by_review.get(rid)
        if not ra_id:
            continue
        sent_label = sent_label_by_review.get(rid, "neutral")
        tmp_row = {
            "review_analysis_id": ra_id,
            "insight_task_id": insight_task_id,
            "review_id": rid,
            "platform": platform,
            "product_id": product_id,
        }
        if sent_label == "positive":
            pos_tmp_rows.append(tmp_row)
        elif sent_label == "negative":
            neg_tmp_rows.append(tmp_row)
        else:
            neu_tmp_rows.append(tmp_row)
        has_dimension_hit = False
        for d in item.get("dimensions") or []:
            if not isinstance(d, dict):
                continue
            dim = d.get("dimension")
            if not dim or str(dim) not in _ALLOWED_DIMS:
                continue
            if not _sentiment_allow_dimension(sent_label, str(dim)):
                continue
            has_dimension_hit = True
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
        if not has_dimension_hit:
            unmatched_rows.append(
                {
                    "review_analysis_id": ra_id,
                    "insight_task_id": insight_task_id,
                    "review_id": rid,
                    "platform": platform,
                    "product_id": product_id,
                    "sentiment_label": sent_label,
                    "reason": "no_dimension_hit",
                }
            )

    # 先落三张临时表，再做六维命中写入
    if pos_tmp_rows:
        sb.table("review_sentiment_positive_tmp").insert(pos_tmp_rows).execute()
    if neu_tmp_rows:
        sb.table("review_sentiment_neutral_tmp").insert(neu_tmp_rows).execute()
    if neg_tmp_rows:
        sb.table("review_sentiment_negative_tmp").insert(neg_tmp_rows).execute()
    if dim_rows:
        sb.table("review_dimension_analysis").insert(dim_rows).execute()
    if unmatched_rows:
        sb.table("review_dimension_unmatched").insert(unmatched_rows).execute()
        for row in unmatched_rows:
            base = {
                "review_analysis_id": row["review_analysis_id"],
                "insight_task_id": row["insight_task_id"],
                "review_id": row["review_id"],
                "platform": row["platform"],
                "product_id": row["product_id"],
                "reason": row.get("reason") or "no_dimension_hit",
            }
            s = row.get("sentiment_label")
            if s == "positive":
                pos_unmatched_rows.append(base)
            elif s == "negative":
                neg_unmatched_rows.append(base)
            else:
                neu_unmatched_rows.append(base)
    if pos_unmatched_rows:
        sb.table("review_sentiment_positive_unmatched").insert(pos_unmatched_rows).execute()
    if neu_unmatched_rows:
        sb.table("review_sentiment_neutral_unmatched").insert(neu_unmatched_rows).execute()
    if neg_unmatched_rows:
        sb.table("review_sentiment_negative_unmatched").insert(neg_unmatched_rows).execute()
