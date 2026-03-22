from __future__ import annotations

import math
from typing import Any


def _coerce_rating(val: Any) -> float | None:
    if val is None:
        return None
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            return None
        return float(val)
    try:
        return float(str(val).strip())
    except (TypeError, ValueError):
        return None


def _pick_text(item: dict[str, Any]) -> str | None:
    for key in (
        "raw_text",
        "text",
        "body",
        "content",
        "reviewText",
        "description",
        "comment",
    ):
        v = item.get(key)
        if v is not None and str(v).strip():
            return str(v).strip()
    return None


def extract_review_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("reviews", "items", "data", "results", "records", "rows"):
        v = payload.get(key)
        if isinstance(v, list):
            return [x for x in v if isinstance(x, dict)]
    return []


def normalize_provider_item(item: dict[str, Any]) -> dict[str, Any] | None:
    """转为可写入 `reviews` 表的字段子集（不含 insight_task_id / platform / product_id）。"""
    raw_text = _pick_text(item)
    if not raw_text:
        return None
    ext = (
        item.get("external_review_id")
        or item.get("review_id")
        or item.get("id")
    )
    external_review_id = str(ext) if ext is not None else None
    title = item.get("title") or item.get("summary")
    title_s = str(title).strip() if title is not None else None
    sku = item.get("sku") or item.get("sku_id")
    sku_s = str(sku).strip() if sku is not None else None
    lang = item.get("lang") or item.get("language")
    lang_s = str(lang).strip() if lang is not None else None
    reviewed_at = item.get("reviewed_at") or item.get("date") or item.get("created_at")
    if reviewed_at is not None and not isinstance(reviewed_at, str):
        reviewed_at = str(reviewed_at)
    known = {
        "raw_text",
        "text",
        "body",
        "content",
        "reviewText",
        "description",
        "comment",
        "external_review_id",
        "review_id",
        "id",
        "title",
        "summary",
        "rating",
        "overall",
        "stars",
        "sku",
        "sku_id",
        "lang",
        "language",
        "reviewed_at",
        "date",
        "created_at",
    }
    extra = {k: v for k, v in item.items() if k not in known}
    rating = _coerce_rating(
        item.get("rating") if item.get("rating") is not None else item.get("overall")
    )
    if rating is None:
        rating = _coerce_rating(item.get("stars"))
    return {
        "external_review_id": external_review_id,
        "raw_text": raw_text,
        "title": title_s,
        "rating": rating,
        "sku": sku_s,
        "reviewed_at": reviewed_at,
        "lang": lang_s,
        "extra": extra or None,
    }
