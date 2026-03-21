"""
TA-7：六维词典归因引擎（可解释子串匹配）。
规则口径见 docs/stage-a/ecommerce-review-insights-v1-ta6-dictionary-and-matching-rules.md
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

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


@dataclass(frozen=True, slots=True)
class PatternRow:
    text: str
    dimension: str
    canonical: str
    priority: int
    weight: float


@dataclass(frozen=True, slots=True)
class Match:
    start: int
    end: int
    dimension: str
    canonical: str
    priority: int


def load_taxonomy_yaml(path: Path | str) -> dict[str, Any]:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid taxonomy yaml: {path}")
    return data


def build_patterns(data: dict[str, Any]) -> list[PatternRow]:
    entries = data.get("entries") or []
    if not isinstance(entries, list):
        raise ValueError("taxonomy.entries must be a list")
    rows: list[PatternRow] = []
    for i, ent in enumerate(entries):
        if not isinstance(ent, dict):
            continue
        dim = str(ent.get("dimension_6way", "")).strip()
        if dim not in DIMENSION_KEYS:
            raise ValueError(f"Invalid dimension_6way at entries[{i}]: {dim!r}")
        canonical = str(ent.get("canonical", "")).strip()
        if not canonical:
            raise ValueError(f"Missing canonical at entries[{i}]")
        aliases = ent.get("aliases") or []
        if isinstance(aliases, str):
            aliases = [aliases]
        if not isinstance(aliases, list):
            aliases = []
        priority = int(ent.get("priority", 0))
        weight = float(ent.get("weight", 1.0))
        phrases = {canonical, *[str(a).strip() for a in aliases if str(a).strip()]}
        for p in phrases:
            if len(p) < 2:
                continue
            rows.append(
                PatternRow(
                    text=p,
                    dimension=dim,
                    canonical=canonical,
                    priority=priority,
                    weight=weight,
                )
            )
    # Longer phrase first, then priority, then stable text for reproducibility
    rows.sort(key=lambda r: (-len(r.text), -r.priority, r.text.lower(), r.dimension))
    return rows


def _find_all_spans(haystack_lower: str, needle_lower: str) -> list[tuple[int, int]]:
    if not needle_lower:
        return []
    out: list[tuple[int, int]] = []
    start = 0
    while True:
        i = haystack_lower.find(needle_lower, start)
        if i < 0:
            break
        out.append((i, i + len(needle_lower)))
        start = i + 1
    return out


def _collect_matches(analysis_input_en: str, patterns: list[PatternRow]) -> list[Match]:
    text = analysis_input_en or ""
    lower = text.lower()
    candidates: list[Match] = []
    for pr in patterns:
        needle = pr.text.lower()
        for s, e in _find_all_spans(lower, needle):
            candidates.append(
                Match(
                    start=s,
                    end=e,
                    dimension=pr.dimension,
                    canonical=pr.canonical,
                    priority=pr.priority,
                )
            )
    candidates.sort(
        key=lambda m: (-(m.end - m.start), -m.priority, m.start, m.dimension, m.canonical)
    )
    selected: list[Match] = []

    def overlaps(a: Match, b: Match) -> bool:
        return not (a.end <= b.start or b.end <= a.start)

    for m in candidates:
        if any(overlaps(m, s) for s in selected):
            continue
        selected.append(m)
    selected.sort(key=lambda m: (m.start, m.end, m.dimension, m.canonical))
    return selected


def _map_evidence_to_raw(raw_text: str, analysis_input_en: str, win_s: int, win_e: int) -> tuple[str, int | None]:
    """Returns (evidence_quote, raw_start_index or None if unmapped)."""
    ain = analysis_input_en or ""
    phrase = ain[win_s:win_e]
    if not phrase:
        return "", None
    raw = raw_text or ""
    idx = raw.lower().find(phrase.lower())
    if idx >= 0:
        return raw[idx : idx + len(phrase)], idx
    return phrase, None


def attribute_review(
    review_id: str,
    raw_text: str,
    analysis_input_en: str,
    patterns: list[PatternRow],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Returns (dimensions_for_contract, debug_meta).
    dimensions shape aligns with packages/contracts Analysis DimensionAnalysis:
      dimension, keywords, evidence_quote, highlight_spans
    """
    ain = analysis_input_en or ""
    matches = _collect_matches(ain, patterns)
    by_dim: dict[str, list[Match]] = {}
    for m in matches:
        by_dim.setdefault(m.dimension, []).append(m)

    dimensions: list[dict[str, Any]] = []
    trace_flags: list[bool] = []

    for dim in sorted(by_dim.keys()):
        ms = by_dim[dim]
        win_s = min(x.start for x in ms)
        win_e = max(x.end for x in ms)
        evidence, raw_idx = _map_evidence_to_raw(raw_text, ain, win_s, win_e)
        trace_flags.append(raw_idx is not None)

        keywords: list[str] = []
        seen: set[str] = set()
        for x in sorted(ms, key=lambda m: (m.start, m.canonical)):
            if x.canonical not in seen:
                seen.add(x.canonical)
                keywords.append(x.canonical)

        # evidence_quote 与 phrase=ain[win_s:win_e] 等长（映射到 raw 时按同长度切片），
        # 高亮区间相对于 evidence_quote 起点 = 命中在窗口内的偏移。
        spans: list[dict[str, Any]] = []
        for x in ms:
            rel_s = x.start - win_s
            rel_e = x.end - win_s
            spans.append(
                {
                    "start": max(0, rel_s),
                    "end": max(0, rel_e),
                    "label": "keyword",
                }
            )

        dimensions.append(
            {
                "dimension": dim,
                "keywords": keywords,
                "evidence_quote": evidence if evidence else None,
                "highlight_spans": spans,
            }
        )

    meta = {
        "review_id": review_id,
        "evidence_mapped_to_raw_text": all(trace_flags) if trace_flags else True,
        "match_count": len(matches),
    }
    return dimensions, meta


def attribute_review_from_yaml_path(
    review_id: str,
    raw_text: str,
    analysis_input_en: str,
    taxonomy_yaml: Path | str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    data = load_taxonomy_yaml(taxonomy_yaml)
    patterns = build_patterns(data)
    return attribute_review(review_id, raw_text, analysis_input_en, patterns)
