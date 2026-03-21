from __future__ import annotations

from typing import Any

# 与 TA-1 冻结六维 key 对齐
DIMENSION_KEYS = frozenset(
    {
        "pros",
        "cons",
        "return_reasons",
        "purchase_motivation",
        "user_expectation",
        "usage_scenario",
    }
)

_SENT_MAP = {
    "negative": "negative",
    "neg": "negative",
    "0": "negative",
    0: "negative",
    "neutral": "neutral",
    "neu": "neutral",
    "1": "neutral",
    1: "neutral",
    "positive": "positive",
    "pos": "positive",
    "2": "positive",
    2: "positive",
}


def _coerce_sentiment_label(v: Any) -> str | None:
    if v is None:
        return None
    if isinstance(v, str):
        key = v.strip().lower()
        return _SENT_MAP.get(key) or _SENT_MAP.get(key.replace(" ", "_"))
    return _SENT_MAP.get(v)


def _pick_sentiment_block(item: dict[str, Any]) -> dict[str, Any] | None:
    if "sentiment" in item and isinstance(item["sentiment"], dict):
        return item["sentiment"]
    if "sentiment_label" in item or "polarity" in item:
        return item
    return None


def _float_or_none(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def extract_analysis_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("reviews", "results", "items", "data", "rows"):
        v = payload.get(key)
        if isinstance(v, list):
            return [x for x in v if isinstance(x, dict)]
    return []


def normalize_dimension_entry(d: dict[str, Any]) -> dict[str, Any] | None:
    dim = d.get("dimension") or d.get("dimension_6way") or d.get("axis")
    if not dim or str(dim).strip() not in DIMENSION_KEYS:
        return None
    dim_s = str(dim).strip()
    keywords = d.get("keywords") or d.get("labels") or d.get("pain_labels") or []
    if isinstance(keywords, str):
        keywords = [keywords]
    if not isinstance(keywords, list):
        keywords = []
    kw_clean = [str(x).strip() for x in keywords if x is not None and str(x).strip()]
    spans = d.get("highlight_spans") or d.get("spans") or []
    if not isinstance(spans, list):
        spans = []
    safe_spans: list[dict[str, Any]] = []
    for s in spans:
        if not isinstance(s, dict):
            continue
        try:
            start = int(s.get("start", -1))
            end = int(s.get("end", -1))
        except (TypeError, ValueError):
            continue
        if start < 0 or end < start:
            continue
        safe_spans.append(
            {
                "start": start,
                "end": end,
                "label": str(s.get("label", "keyword")),
            }
        )
    eq = d.get("evidence_quote") or d.get("evidence") or d.get("quote")
    return {
        "dimension": dim_s,
        "keywords": kw_clean,
        "evidence_quote": str(eq).strip() if eq is not None else None,
        "highlight_spans": safe_spans,
    }


def normalize_analysis_item(
    item: dict[str, Any],
    fallback_review_id: str | None,
) -> dict[str, Any] | None:
    rid = (
        item.get("review_id")
        or item.get("id")
        or item.get("reviewId")
        or fallback_review_id
    )
    if rid is None:
        return None
    rid_s = str(rid)

    sent_block = _pick_sentiment_block(item)
    label: str | None = None
    conf: float | None = None
    if sent_block:
        label = _coerce_sentiment_label(
            sent_block.get("label")
            or sent_block.get("sentiment")
            or sent_block.get("polarity")
            or sent_block.get("class")
        )
        conf = _float_or_none(
            sent_block.get("confidence")
            or sent_block.get("score")
            or sent_block.get("prob")
        )
    if label is None:
        label = _coerce_sentiment_label(item.get("label_sentiment"))

    if label is None:
        label = "neutral"
        conf = conf if conf is not None else None

    dims_raw = item.get("dimensions") or item.get("dimension_hits") or item.get("six_dim") or []
    if not isinstance(dims_raw, list):
        dims_raw = []
    dimensions: list[dict[str, Any]] = []
    for d in dims_raw:
        if not isinstance(d, dict):
            continue
        norm = normalize_dimension_entry(d)
        if norm:
            dimensions.append(norm)

    return {
        "review_id": rid_s,
        "sentiment": {"label": label, "confidence": conf},
        "dimensions": dimensions,
    }


def build_canonical_response(
    payload: Any,
    review_ids_in_order: list[str],
) -> list[dict[str, Any]]:
    """将提供商 JSON 规范为统一列表；按已知 review_id 匹配，否则按顺序对齐。"""
    raw_list = extract_analysis_list(payload)
    out: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    for item in raw_list:
        norm = normalize_analysis_item(item, None)
        if norm:
            by_id[norm["review_id"]] = norm

    for i, rid in enumerate(review_ids_in_order):
        if rid in by_id:
            out.append(by_id[rid])
            continue
        if i < len(raw_list):
            norm = normalize_analysis_item(raw_list[i], rid)
            if norm:
                out.append(norm)
                continue
        out.append(
            {
                "review_id": rid,
                "sentiment": {"label": "neutral", "confidence": None},
                "dimensions": [],
            }
        )
    return out
