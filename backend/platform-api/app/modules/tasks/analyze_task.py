from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from supabase import Client

from app.core.config import get_settings
from app.integrations.agent_enrichment import enrich_normalized_analyses
from app.integrations.analysis_provider import AnalysisProviderError, analyze_reviews
from app.modules.analysis_results.persist import replace_task_analysis
from app.modules.tasks import state_machine
from app.modules.tasks.listing import enrich_task_for_task_center

log = logging.getLogger("rsa.analyze_task")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_analyze_for_task(
    sb: Client, task_id: UUID, *, force_reanalyze: bool = False
) -> dict:
    """对任务已落库的 reviews 调用分析源；成功则写入 TB-4 表后 running→success，失败则 failed（failure_stage=analyze）。"""
    res = (
        sb.table("insight_tasks")
        .select("*")
        .eq("id", str(task_id))
        .limit(1)
        .execute()
    )
    rows = res.data or []
    if not rows:
        raise HTTPException(status_code=404, detail="任务不存在")
    task = rows[0]
    status = task["status"]

    if status == "success":
        if not force_reanalyze:
            raise HTTPException(status_code=409, detail="任务已成功完成分析，无需重复执行")
        try:
            state_machine.assert_valid_transition("success", "running")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        up = (
            sb.table("insight_tasks")
            .update(
                {
                    "status": "running",
                    "updated_at": _utc_now_iso(),
                    "error_code": None,
                    "error_message": None,
                    "failure_stage": None,
                    "ai_summary": None,
                }
            )
            .eq("id", str(task_id))
            .execute()
        )
        if not up.data:
            raise HTTPException(status_code=500, detail="无法将任务置为 running 以重新分析")
        task = up.data[0]
        status = task["status"]

    if status == "pending":
        raise HTTPException(
            status_code=400,
            detail="请先完成评论抓取（POST .../fetch-reviews）后再分析",
        )
    if status == "cancelled":
        raise HTTPException(status_code=409, detail="任务已取消，不可分析")
    if status == "failed":
        raise HTTPException(
            status_code=400,
            detail="任务已失败：请用 PATCH 将状态改为 pending 后重新抓取与分析",
        )
    if status != "running":
        raise HTTPException(status_code=400, detail=f"当前状态 {status!r} 不可触发分析")

    rv = (
        sb.table("reviews")
        .select("id,raw_text,title,rating,sku,reviewed_at,lang")
        .eq("insight_task_id", str(task_id))
        .order("created_at")
        .execute()
    )
    review_rows = rv.data or []
    if not review_rows:
        raise HTTPException(
            status_code=400,
            detail="没有已抓取的评论，请先执行 fetch-reviews",
        )

    settings = get_settings()
    agent_stats: dict | None = None
    try:
        effective_id, normalized, _raw = analyze_reviews(
            insight_task_id=str(task_id),
            platform=task["platform"],
            product_id=task["product_id"],
            task_analysis_provider_id=task.get("analysis_provider_id"),
            reviews=review_rows,
            dictionary_vertical_id=task.get("dictionary_vertical_id"),
            settings=settings,
        )
    except AnalysisProviderError as e:
        sb.table("insight_tasks").update(
            {
                "status": "failed",
                "updated_at": _utc_now_iso(),
                "error_code": e.code,
                "error_message": e.message[:4000],
                "failure_stage": "analyze",
            }
        ).eq("id", str(task_id)).execute()
        raise HTTPException(
            status_code=502,
            detail=f"{e.code}: {e.message}",
        ) from e

    url = (settings.agent_enrichment_url or "").strip()
    inline_agent = bool(url) and (
        settings.agent_gap_fill_enabled or float(settings.agent_sample_fraction or 0) > 0
    )
    if inline_agent and not settings.agent_gap_fill_deferred:
        try:
            normalized, agent_stats = enrich_normalized_analyses(
                settings=settings,
                insight_task_id=str(task_id),
                platform=task["platform"],
                product_id=task["product_id"],
                dictionary_vertical_id=task.get("dictionary_vertical_id"),
                reviews=review_rows,
                normalized=normalized,
            )
        except Exception as e:  # noqa: BLE001
            agent_stats = {
                "enabled": True,
                "error": f"{type(e).__name__}: {e!s}",
            }

    try:
        replace_task_analysis(
            sb,
            insight_task_id=str(task_id),
            platform=task["platform"],
            product_id=task["product_id"],
            analysis_provider_id=effective_id,
            review_analyses=normalized,
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"分析结果落库失败：{e!s}",
        ) from e

    up = (
        sb.table("insight_tasks")
        .update(
            {
                "status": "success",
                "updated_at": _utc_now_iso(),
                "error_code": None,
                "error_message": None,
                "failure_stage": None,
            }
        )
        .eq("id", str(task_id))
        .execute()
    )
    if not up.data:
        raise HTTPException(status_code=500, detail="更新任务为 success 失败")
    task_row = up.data[0]

    if settings.insight_summary_auto_after_analyze:
        _spawn_ai_summary_async(sb, task_id)
    if settings.topic_discovery_auto_after_analyze:
        _spawn_topic_discovery_async(
            sb,
            task_id,
            embedding_model=(settings.topic_discovery_auto_embedding_model or "").strip()
            or "ml/all-MiniLM-L6-v2",
        )

    out: dict = {
        "task": enrich_task_for_task_center(task_row),
        "analysis_provider_id_used": effective_id,
        "review_analyses": normalized,
    }
    if agent_stats is not None:
        out["agent_enrichment"] = agent_stats
    return out


def _spawn_ai_summary_async(sb: Client, task_id: UUID) -> None:
    """analyze 成功后后台触发一次 AI 摘要（force regenerate）；失败仅日志，不影响 analyze 返回。"""

    def _runner() -> None:
        try:
            from app.modules.insight_summary.service import run_insight_ai_summary

            run_insight_ai_summary(sb, task_id, regenerate=True)
            log.info("ai_summary auto-generated for task=%s", task_id)
        except Exception as e:  # noqa: BLE001
            log.warning("ai_summary auto-generate failed for task=%s: %s", task_id, e)

    threading.Thread(
        target=_runner,
        name=f"ai-summary-{str(task_id)[:8]}",
        daemon=True,
    ).start()


def _spawn_topic_discovery_async(sb: Client, task_id: UUID, *, embedding_model: str) -> None:
    """analyze 成功后后台触发单任务主题挖掘；若已有进行中任务则跳过。"""

    def _runner() -> None:
        try:
            from app.modules.tasks.topic_discovery_jobs import create_job, get_latest_for_task

            latest = get_latest_for_task(sb, task_id)
            if latest and latest.get("status") in ("pending", "running"):
                log.info(
                    "topic_discovery auto-skip for task=%s: job already %s",
                    task_id,
                    latest.get("status"),
                )
                return

            job = create_job(
                sb,
                insight_task_id=task_id,
                embedding_model=embedding_model,
                dry_run=False,
            )
            log.info(
                "topic_discovery auto-triggered for task=%s job=%s",
                task_id,
                job.get("id"),
            )
        except Exception as e:  # noqa: BLE001
            log.warning("topic_discovery auto-trigger failed for task=%s: %s", task_id, e)

    threading.Thread(
        target=_runner,
        name=f"topic-discovery-{str(task_id)[:8]}",
        daemon=True,
    ).start()
