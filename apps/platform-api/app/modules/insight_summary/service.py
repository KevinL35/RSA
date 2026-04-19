"""TB-5 扩展：基于看板聚合数据调用 DeepSeek 适配层生成 AI 洞察摘要，并写入 insight_tasks.ai_summary。"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx
from fastapi import HTTPException
from supabase import Client

from app.core.config import get_settings
from app.modules.insight_dashboard.service import build_insight_dashboard


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fingerprint_from_dashboard(d: dict[str, Any]) -> str:
    """分析结果变化时指纹变化，用于缓存失效。"""
    pr = d.get("pain_ranking") or []
    pr_key = [
        {"k": x.get("keyword"), "c": x.get("count"), "d": sorted(x.get("dimensions") or [])}
        for x in pr[:25]
        if isinstance(x, dict)
    ]
    dc = d.get("dimension_counts") or {}
    payload = {
        "pain_ranking": pr_key,
        "dimension_counts": dict(sorted(dc.items())) if isinstance(dc, dict) else {},
        "matched_review_count": d.get("matched_review_count"),
        "review_total_count": d.get("review_total_count"),
        "analyzed_at": d.get("analyzed_at"),
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _build_context_for_llm(d: dict[str, Any]) -> dict[str, Any]:
    items = d.get("evidence") or {}
    ev_list = items.get("items") or []
    samples: list[dict[str, Any]] = []
    for h in ev_list[:18]:
        if not isinstance(h, dict):
            continue
        quote = (h.get("evidence_quote") or "").strip()
        if not quote and h.get("review"):
            rt = h.get("review") or {}
            quote = str(rt.get("raw_text") or "")[:500]
        samples.append(
            {
                "dimension": h.get("dimension"),
                "keywords": (h.get("keywords") or [])[:6],
                "quote": (quote or "")[:450],
            }
        )
    pr = d.get("pain_ranking") or []
    top_kw = [
        {"keyword": x.get("keyword"), "count": x.get("count"), "dimensions": x.get("dimensions")}
        for x in pr[:15]
        if isinstance(x, dict)
    ]
    snap_raw = d.get("product_snapshot") or {}
    snapshot: dict[str, Any] = {}
    if isinstance(snap_raw, dict):
        for k in ("title", "price_display", "image_url", "asin", "source", "fetched_at"):
            v = snap_raw.get(k)
            if v not in (None, ""):
                snapshot[k] = v
    return {
        "product_id": d.get("product_id"),
        "platform": d.get("platform"),
        "product_snapshot": snapshot or None,
        "dictionary_vertical_id": d.get("dictionary_vertical_id"),
        "review_total_count": d.get("review_total_count"),
        "matched_review_count": d.get("matched_review_count"),
        "dimension_counts": d.get("dimension_counts") or {},
        "pain_ranking_top": top_kw,
        "sample_evidence_quotes": samples,
    }


def _call_insight_summary_adapter(*, context: dict[str, Any]) -> tuple[str, str]:
    settings = get_settings()
    url = (settings.insight_summary_url or "").strip()
    if not url:
        raise HTTPException(
            status_code=503,
            detail="未配置 INSIGHT_SUMMARY_URL（通常为 http://127.0.0.1:9100/insight-summary）",
        )
    headers: dict[str, str] = {"Content-Type": "application/json", "Accept": "application/json"}
    key = (settings.insight_summary_api_key or "").strip()
    if key:
        headers["Authorization"] = f"Bearer {key}"
    timeout = float(settings.insight_summary_timeout_seconds or 120.0)
    body = {"context": context}
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=body, headers=headers)
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"AI 摘要服务不可达：{e!s}") from e
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"AI 摘要服务错误 HTTP {resp.status_code}: {resp.text[:1200]}",
        )
    try:
        payload = resp.json()
    except ValueError as e:
        raise HTTPException(status_code=502, detail=f"AI 摘要响应非 JSON：{e!s}") from e
    summary = (payload.get("summary") or "").strip()
    if not summary:
        raise HTTPException(status_code=502, detail="AI 摘要为空")
    model = str(payload.get("model") or "deepseek")
    return summary, model


def run_insight_ai_summary(
    sb: Client,
    task_id: UUID,
    *,
    regenerate: bool = False,
) -> dict[str, Any]:
    tr = (
        sb.table("insight_tasks")
        .select("id,status,ai_summary,updated_at")
        .eq("id", str(task_id))
        .limit(1)
        .execute()
    )
    rows = tr.data or []
    if not rows:
        raise HTTPException(status_code=404, detail="任务不存在")
    task = rows[0]
    if task.get("status") != "success":
        raise HTTPException(status_code=400, detail="仅分析成功的任务可生成 AI 摘要")

    dash = build_insight_dashboard(
        sb,
        task_id,
        evidence_limit=60,
        evidence_offset=0,
        evidence_dimension=None,
    )
    if dash.get("_not_found") or dash.get("empty_state"):
        raise HTTPException(
            status_code=400,
            detail="看板数据不可用，无法生成 AI 摘要（任务须已成功且含六维命中）",
        )

    fp = _fingerprint_from_dashboard(dash)
    existing = task.get("ai_summary")
    if (
        not regenerate
        and isinstance(existing, dict)
        and (existing.get("fingerprint") or "") == fp
        and (existing.get("text") or "").strip()
    ):
        return {
            "cached": True,
            "ai_summary": existing,
            "fingerprint": fp,
        }

    context = _build_context_for_llm(dash)
    text, model = _call_insight_summary_adapter(context=context)
    gen_at = _utc_now_iso()
    blob: dict[str, Any] = {
        "text": text,
        "model": model,
        "generated_at": gen_at,
        "fingerprint": fp,
    }
    up = (
        sb.table("insight_tasks")
        .update({"ai_summary": blob})
        .eq("id", str(task_id))
        .execute()
    )
    if not up.data:
        raise HTTPException(status_code=500, detail="写入 ai_summary 失败")
    return {
        "cached": False,
        "ai_summary": blob,
        "fingerprint": fp,
    }
