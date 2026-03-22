from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from supabase import Client

from app.core.config import get_settings
from app.integrations.analysis_provider import AnalysisProviderError, analyze_reviews
from app.modules.analysis_results.persist import replace_task_analysis
from app.modules.tasks.listing import enrich_task_for_task_center


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_analyze_for_task(sb: Client, task_id: UUID) -> dict:
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

    if status == "pending":
        raise HTTPException(
            status_code=400,
            detail="请先完成评论抓取（POST .../fetch-reviews）后再分析",
        )
    if status == "success":
        raise HTTPException(status_code=409, detail="任务已成功完成分析，无需重复执行")
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

    return {
        "task": enrich_task_for_task_center(task_row),
        "analysis_provider_id_used": effective_id,
        "review_analyses": normalized,
    }
