"""组合情感 + 六维归因，输出与 TB-3 契约兼容的逐条结果。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
_TOPIC_MINING_SCRIPTS = _REPO_ROOT / "ml" / "topic_mining" / "scripts"
if str(_TOPIC_MINING_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_TOPIC_MINING_SCRIPTS))

from attribution_engine import (  # noqa: E402
    PatternRow,
    attribute_review,
    build_patterns,
    load_taxonomy_yaml,
)

from .sentiment import predict_sentiment
from .taxonomy_config import load_merged_taxonomy_dict

_patterns_by_vertical: dict[str, list[PatternRow]] = {}


def get_patterns(
    *,
    dictionary_vertical_id: str | None,
    taxonomy_path: Path | None,
) -> list[PatternRow]:
    """TAXONOMY_YAML 显式指定时忽略 vertical；否则按 vertical 合并 seed+overlay（与 API 预览一致）。"""
    global _patterns_by_vertical
    if taxonomy_path is not None:
        cache_key = f"file:{taxonomy_path.resolve()}"
        if cache_key not in _patterns_by_vertical:
            data = load_taxonomy_yaml(taxonomy_path)
            _patterns_by_vertical[cache_key] = build_patterns(data)
        return _patterns_by_vertical[cache_key]
    vid = (dictionary_vertical_id or "general").strip() or "general"
    if vid not in _patterns_by_vertical:
        data = load_merged_taxonomy_dict(vid)
        _patterns_by_vertical[vid] = build_patterns(data)
    return _patterns_by_vertical[vid]


def reset_patterns_cache() -> None:
    global _patterns_by_vertical
    _patterns_by_vertical = {}


def analyze_reviews_body(
    body: dict[str, Any],
    *,
    taxonomy_path: Path | None = None,
) -> list[dict[str, Any]]:
    reviews = body.get("reviews") or []
    if not isinstance(reviews, list):
        reviews = []
    dvid = body.get("dictionary_vertical_id")
    if dvid is not None:
        dvid = str(dvid).strip() or None
    patterns = get_patterns(dictionary_vertical_id=dvid, taxonomy_path=taxonomy_path)
    out: list[dict[str, Any]] = []
    for r in reviews:
        if not isinstance(r, dict):
            continue
        rid = str(r.get("id") or "")
        raw = str(r.get("raw_text") or "")
        rating = r.get("rating")
        rating_f: float | None
        try:
            rating_f = float(rating) if rating is not None else None
        except (TypeError, ValueError):
            rating_f = None
        # 在线评论表无 analysis_input_en 列时，用原文做词典匹配（英文评论场景）
        ain = str(r.get("analysis_input_en") or raw)
        sent_label, sent_conf = predict_sentiment(raw, rating_f)
        dims, _meta = attribute_review(rid, raw, ain, patterns)
        out.append(
            {
                "review_id": rid,
                "sentiment": {"label": sent_label, "confidence": sent_conf},
                "dimensions": dims,
            }
        )
    return out
