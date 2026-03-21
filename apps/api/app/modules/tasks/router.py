from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.integrations.supabase import require_supabase

from . import state_machine
from .fetch_reviews import run_fetch_reviews_for_task
from .schema import InsightTaskCreate, InsightTaskPatch

router = APIRouter(prefix="/api/v1/insight-tasks", tags=["insight-tasks"])


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("")
def list_insight_tasks() -> dict:
    try:
        sb = require_supabase()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    try:
        res = (
            sb.table("insight_tasks")
            .select("*")
            .order("created_at", desc=True)
            .limit(200)
            .execute()
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=502,
            detail=f"Supabase 查询失败：{e!s}",
        ) from e
    return {"items": res.data or []}


@router.post("")
def create_insight_task(body: InsightTaskCreate) -> dict:
    try:
        sb = require_supabase()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    row = {
        "platform": body.platform.strip(),
        "product_id": body.product_id.strip(),
        "status": "pending",
        "analysis_provider_id": body.analysis_provider_id,
    }
    try:
        res = sb.table("insight_tasks").insert(row).select("*").execute()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=502,
            detail=f"Supabase 写入失败：{e!s}",
        ) from e
    data = res.data
    if not data:
        raise HTTPException(status_code=500, detail="插入成功但未返回数据，请检查 RLS/策略")
    return data[0]


@router.post("/{task_id}/fetch-reviews")
def post_fetch_reviews(task_id: UUID) -> dict:
    """TB-2：按任务 platform/product_id 调用评论抓取 API 并写入 reviews。"""
    try:
        sb = require_supabase()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    try:
        return run_fetch_reviews_for_task(sb, task_id)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"抓取流程异常：{e!s}",
        ) from e


@router.get("/{task_id}")
def get_insight_task(task_id: UUID) -> dict:
    try:
        sb = require_supabase()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    try:
        res = (
            sb.table("insight_tasks")
            .select("*")
            .eq("id", str(task_id))
            .limit(1)
            .execute()
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=502,
            detail=f"Supabase 查询失败：{e!s}",
        ) from e
    rows = res.data or []
    if not rows:
        raise HTTPException(status_code=404, detail="任务不存在")
    return rows[0]


@router.patch("/{task_id}")
def patch_insight_task(task_id: UUID, body: InsightTaskPatch) -> dict:
    try:
        sb = require_supabase()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    try:
        cur = (
            sb.table("insight_tasks")
            .select("status")
            .eq("id", str(task_id))
            .limit(1)
            .execute()
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=502,
            detail=f"Supabase 查询失败：{e!s}",
        ) from e
    rows = cur.data or []
    if not rows:
        raise HTTPException(status_code=404, detail="任务不存在")
    current_status = rows[0]["status"]
    try:
        state_machine.assert_valid_transition(current_status, body.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if body.status == "failed":
        if state_machine.is_failed_transition_invalid(
            body.failure_stage, body.error_message
        ):
            raise HTTPException(
                status_code=400,
                detail="迁移到 failed 时必须提供非空的 failure_stage 与 error_message",
            )

    update: dict = {"status": body.status, "updated_at": _utc_now_iso()}
    if state_machine.should_clear_errors(body.status):
        update["error_code"] = None
        update["error_message"] = None
        update["failure_stage"] = None
    elif body.status == "failed":
        update["error_code"] = body.error_code
        update["error_message"] = body.error_message.strip() if body.error_message else None
        update["failure_stage"] = body.failure_stage.strip() if body.failure_stage else None

    try:
        res = (
            sb.table("insight_tasks")
            .update(update)
            .eq("id", str(task_id))
            .select("*")
            .execute()
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=502,
            detail=f"Supabase 更新失败：{e!s}",
        ) from e
    data = res.data
    if not data:
        raise HTTPException(status_code=500, detail="更新成功但未返回数据，请检查 RLS/策略")
    return data[0]
