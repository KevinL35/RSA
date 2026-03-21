"""组合情感 + 六维归因，输出与 TB-3 契约兼容的逐条结果。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ML_SCRIPTS = _REPO_ROOT / "ml" / "scripts"
if str(_ML_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_ML_SCRIPTS))

from attribution_engine import (  # noqa: E402
    PatternRow,
    attribute_review,
    build_patterns,
    load_taxonomy_yaml,
)

from .sentiment import predict_sentiment

_patterns: list[PatternRow] | None = None


def get_patterns(taxonomy_path: Path | None) -> list[PatternRow]:
    global _patterns
    if _patterns is not None:
        return _patterns
    path = taxonomy_path or (_REPO_ROOT / "ml" / "configs" / "taxonomy_dictionary_seed_v1.yaml")
    data = load_taxonomy_yaml(path)
    _patterns = build_patterns(data)
    return _patterns


def reset_patterns_cache() -> None:
    global _patterns
    _patterns = None


def analyze_reviews_body(
    body: dict[str, Any],
    *,
    taxonomy_path: Path | None = None,
) -> list[dict[str, Any]]:
    reviews = body.get("reviews") or []
    if not isinstance(reviews, list):
        reviews = []
    patterns = get_patterns(taxonomy_path)
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
