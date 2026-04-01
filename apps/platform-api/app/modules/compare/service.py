from __future__ import annotations

from collections import Counter
from typing import Any

from supabase import Client

_DIMS = (
    "pros",
    "cons",
    "return_reasons",
    "purchase_motivation",
    "user_expectation",
    "usage_scenario",
)


def _latest_success_task(sb: Client, platform: str, product_id: str) -> dict[str, Any] | None:
    res = (
        sb.table("insight_tasks")
        .select("id,platform,product_id,updated_at")
        .eq("platform", platform.strip())
        .eq("product_id", product_id.strip())
        .eq("status", "success")
        .order("updated_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def _sentiment_counts(sb: Client, task_id: str) -> dict[str, int]:
    res = (
        sb.table("review_analysis")
        .select("sentiment_label")
        .eq("insight_task_id", task_id)
        .execute()
    )
    c: Counter[str] = Counter()
    for row in res.data or []:
        lab = row.get("sentiment_label") or "neutral"
        if lab not in ("negative", "neutral", "positive"):
            lab = "neutral"
        c[lab] += 1
    return {k: c.get(k, 0) for k in ("negative", "neutral", "positive")}


def _dimension_counts(sb: Client, task_id: str) -> dict[str, int]:
    res = (
        sb.table("review_dimension_analysis")
        .select("dimension")
        .eq("insight_task_id", task_id)
        .execute()
    )
    c: Counter[str] = Counter()
    for row in res.data or []:
        d = row.get("dimension")
        if d in _DIMS:
            c[str(d)] += 1
    return {k: c.get(k, 0) for k in _DIMS}


def _keyword_counts(sb: Client, task_id: str) -> Counter[str]:
    res = (
        sb.table("review_dimension_analysis")
        .select("keywords")
        .eq("insight_task_id", task_id)
        .execute()
    )
    c: Counter[str] = Counter()
    for row in res.data or []:
        kws = row.get("keywords") or []
        if not isinstance(kws, list):
            continue
        for raw in kws:
            if raw is None:
                continue
            kw = str(raw).strip().lower()
            if kw:
                c[kw] += 1
    return c


def _top_keywords(counter: Counter[str], n: int = 20) -> list[dict[str, Any]]:
    return [{"keyword": k, "count": v} for k, v in counter.most_common(n)]


def _delta_map(a: dict[str, int], b: dict[str, int], keys: tuple[str, ...]) -> dict[str, int]:
    return {k: a.get(k, 0) - b.get(k, 0) for k in keys}


def _conclusion_cards(
    sent_a: dict[str, int],
    sent_b: dict[str, int],
    dim_a: dict[str, int],
    dim_b: dict[str, int],
    kw_a: Counter[str],
    kw_b: Counter[str],
) -> list[dict[str, Any]]:
    """规则结论文案（英文，便于与 PRD 分析展示一致；TB-11 再做多语言）。"""
    cards: list[dict[str, Any]] = []
    ta = sum(sent_a.values()) or 1
    tb = sum(sent_b.values()) or 1
    pa, pb = sent_a.get("positive", 0) / ta, sent_b.get("positive", 0) / tb
    if abs(pa - pb) >= 0.03:
        side = "A" if pa > pb else "B"
        cards.append(
            {
                "kind": "sentiment",
                "title": "Positive share",
                "detail": (
                    f"Product {side} has a higher share of positive reviews "
                    f"({max(pa, pb):.0%} vs {min(pa, pb):.0%})."
                ),
            }
        )

    # 六维：哪边 cons 命中更多（相对）
    ca, cb = dim_a.get("cons", 0), dim_b.get("cons", 0)
    if ca + cb > 0 and ca != cb:
        side = "A" if ca > cb else "B"
        cards.append(
            {
                "kind": "dimension",
                "title": "Pain in cons",
                "detail": (
                    f"Product {side} shows more cons-dimension hits ({max(ca, cb)} vs {min(ca, cb)})."
                ),
            }
        )

    # 关键词：仅出现在一侧的 Top 词
    set_a = set(kw_a.keys())
    set_b = set(kw_b.keys())
    only_a = set_a - set_b
    only_b = set_b - set_a
    if only_a:
        top = sorted(only_a, key=lambda k: kw_a[k], reverse=True)[:3]
        cards.append(
            {
                "kind": "keyword",
                "title": "Keywords more specific to A",
                "detail": "Top distinct keywords: " + ", ".join(top),
            }
        )
    if only_b:
        top = sorted(only_b, key=lambda k: kw_b[k], reverse=True)[:3]
        cards.append(
            {
                "kind": "keyword",
                "title": "Keywords more specific to B",
                "detail": "Top distinct keywords: " + ", ".join(top),
            }
        )

    if not cards:
        cards.append(
            {
                "kind": "summary",
                "title": "Overview",
                "detail": "Both products show similar aggregate signals in this snapshot; drill down into dimensions and evidence for details.",
            }
        )
    return cards[:8]


def build_product_compare(
    sb: Client,
    *,
    platform_a: str,
    product_id_a: str,
    platform_b: str,
    product_id_b: str,
) -> dict[str, Any]:
    ta = _latest_success_task(sb, platform_a, product_id_a)
    tb = _latest_success_task(sb, platform_b, product_id_b)
    reasons: dict[str, str | None] = {"a": None, "b": None}
    if ta is None:
        reasons["a"] = "no_success_task"
    if tb is None:
        reasons["b"] = "no_success_task"
    if ta is None or tb is None:
        return {
            "_missing": True,
            "reasons": reasons,
            "products": {
                "a": {
                    "platform": platform_a.strip(),
                    "product_id": product_id_a.strip(),
                    "insight_task_id": str(ta["id"]) if ta else None,
                },
                "b": {
                    "platform": platform_b.strip(),
                    "product_id": product_id_b.strip(),
                    "insight_task_id": str(tb["id"]) if tb else None,
                },
            },
        }

    id_a, id_b = str(ta["id"]), str(tb["id"])
    sent_a, sent_b = _sentiment_counts(sb, id_a), _sentiment_counts(sb, id_b)
    if sum(sent_a.values()) == 0:
        reasons["a"] = "empty_analysis"
    if sum(sent_b.values()) == 0:
        reasons["b"] = "empty_analysis"
    if reasons["a"] or reasons["b"]:
        return {
            "_missing": True,
            "reasons": reasons,
            "products": {
                "a": {
                    "platform": ta["platform"],
                    "product_id": ta["product_id"],
                    "insight_task_id": id_a,
                },
                "b": {
                    "platform": tb["platform"],
                    "product_id": tb["product_id"],
                    "insight_task_id": id_b,
                },
            },
        }
    dim_a, dim_b = _dimension_counts(sb, id_a), _dimension_counts(sb, id_b)
    kw_a, kw_b = _keyword_counts(sb, id_a), _keyword_counts(sb, id_b)

    delta_sent = _delta_map(sent_a, sent_b, ("negative", "neutral", "positive"))
    delta_dim = _delta_map(dim_a, dim_b, _DIMS)

    def _relative_more(a: Counter[str], b: Counter[str]) -> Counter[str]:
        return Counter({k: a[k] - b.get(k, 0) for k in a if a[k] > b.get(k, 0)})

    more_in_a = _top_keywords(_relative_more(kw_a, kw_b), 15)
    more_in_b = _top_keywords(_relative_more(kw_b, kw_a), 15)

    cards = _conclusion_cards(sent_a, sent_b, dim_a, dim_b, kw_a, kw_b)

    return {
        "product_a": {
            "platform": ta["platform"],
            "product_id": ta["product_id"],
            "insight_task_id": id_a,
        },
        "product_b": {
            "platform": tb["platform"],
            "product_id": tb["product_id"],
            "insight_task_id": id_b,
        },
        "sentiment": {
            "a": sent_a,
            "b": sent_b,
            "delta": delta_sent,
        },
        "dimensions": {
            "a": dim_a,
            "b": dim_b,
            "delta": delta_dim,
        },
        "keywords": {
            "a": _top_keywords(kw_a, 20),
            "b": _top_keywords(kw_b, 20),
            "relative_more_in_a": more_in_a,
            "relative_more_in_b": more_in_b,
        },
        "conclusion_cards": cards,
    }
