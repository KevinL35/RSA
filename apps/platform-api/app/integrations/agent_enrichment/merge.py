"""词典分析结果与 Agent 返回的合并（补洞 / 抽检关键词合并）。"""

from __future__ import annotations

from typing import Any


def _kw_key(s: str) -> str:
    return str(s).strip().lower()


def dedupe_keywords(keywords: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in keywords:
        t = str(x).strip()
        if not t:
            continue
        k = _kw_key(t)
        if k in seen:
            continue
        seen.add(k)
        out.append(t)
    return out


def is_dictionary_gap(item: dict[str, Any]) -> bool:
    """无六维行，或所有维度关键词均为空，视为词典未覆盖、可由 Agent 补洞。"""
    dims = item.get("dimensions") or []
    if not isinstance(dims, list) or not dims:
        return True
    any_kw = False
    for d in dims:
        if not isinstance(d, dict):
            continue
        kws = d.get("keywords") or []
        if not isinstance(kws, list):
            continue
        for x in kws:
            if str(x).strip():
                any_kw = True
                break
        if any_kw:
            break
    return not any_kw


def merge_gap_fill(base: dict[str, Any], agent: dict[str, Any]) -> dict[str, Any]:
    """补洞：Agent 有维度输出则采用其情感与维度；否则保留词典结果。"""
    adims = agent.get("dimensions") or []
    if isinstance(adims, list) and len(adims) > 0:
        sent = agent.get("sentiment") if isinstance(agent.get("sentiment"), dict) else None
        return {
            "review_id": base["review_id"],
            "sentiment": sent or base.get("sentiment") or {"label": "neutral", "confidence": None},
            "dimensions": adims,
        }
    return base


def merge_sample_keywords(base: dict[str, Any], agent: dict[str, Any]) -> dict[str, Any]:
    """抽检：在词典结果上合并 Agent 给出的关键词与同维证据（去重）。"""
    base_dims = base.get("dimensions") or []
    if not isinstance(base_dims, list):
        base_dims = []
    agent_dims = agent.get("dimensions") or []
    if not isinstance(agent_dims, list):
        agent_dims = []

    by_dim: dict[str, dict[str, Any]] = {}
    for d in base_dims:
        if not isinstance(d, dict) or not d.get("dimension"):
            continue
        ds = str(d["dimension"])
        by_dim[ds] = {
            "dimension": ds,
            "keywords": list(d.get("keywords") or []) if isinstance(d.get("keywords"), list) else [],
            "evidence_quote": d.get("evidence_quote"),
            "highlight_spans": list(d.get("highlight_spans") or [])
            if isinstance(d.get("highlight_spans"), list)
            else [],
        }

    for ad in agent_dims:
        if not isinstance(ad, dict) or not ad.get("dimension"):
            continue
        ds = str(ad["dimension"])
        akws = ad.get("keywords") or []
        if not isinstance(akws, list):
            akws = []
        if ds not in by_dim:
            by_dim[ds] = {
                "dimension": ds,
                "keywords": [],
                "evidence_quote": ad.get("evidence_quote"),
                "highlight_spans": list(ad.get("highlight_spans") or [])
                if isinstance(ad.get("highlight_spans"), list)
                else [],
            }
        cur = by_dim[ds]
        cur["keywords"] = dedupe_keywords(
            [str(x) for x in cur["keywords"] if x is not None]
            + [str(x) for x in akws if x is not None],
        )
        if not cur.get("evidence_quote") and ad.get("evidence_quote"):
            cur["evidence_quote"] = ad.get("evidence_quote")
        if isinstance(ad.get("highlight_spans"), list):
            cur_hs = cur.get("highlight_spans") or []
            cur["highlight_spans"] = list(cur_hs) + [x for x in ad["highlight_spans"] if isinstance(x, dict)]

    order: list[str] = []
    for d in base_dims:
        if isinstance(d, dict) and d.get("dimension"):
            ds = str(d["dimension"])
            if ds not in order:
                order.append(ds)
    out_dims: list[dict[str, Any]] = []
    seen: set[str] = set()
    for ds in order:
        if ds in by_dim:
            out_dims.append(by_dim[ds])
            seen.add(ds)
    for ds in sorted(by_dim.keys()):
        if ds not in seen:
            out_dims.append(by_dim[ds])
            seen.add(ds)

    return {
        "review_id": base["review_id"],
        "sentiment": base.get("sentiment") or {"label": "neutral", "confidence": None},
        "dimensions": out_dims,
    }
