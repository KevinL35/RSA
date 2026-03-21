from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from supabase import Client

from app.modules.tasks import state_machine
from app.modules.tasks.listing import enrich_task_for_task_center


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def retry_insight_task(sb: Client, task_id: UUID) -> dict:
    """
    TB-6：幂等重试。failed → pending 并清空错误；已为 pending 则 no-op。
    running / success / cancelled 拒绝。
    """
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
        return {
            "task": enrich_task_for_task_center(task),
            "idempotent": True,
            "action": "none",
            "message": "任务已是 pending，无需重试重置",
        }

    if status == "failed":
        try:
            state_machine.assert_valid_transition("failed", "pending")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        up = (
            sb.table("insight_tasks")
            .update(
                {
                    "status": "pending",
                    "updated_at": _utc_now_iso(),
                    "error_code": None,
                    "error_message": None,
                    "failure_stage": None,
                }
            )
            .eq("id", str(task_id))
            .select("*")
            .execute()
        )
        if not up.data:
            raise HTTPException(status_code=500, detail="重试重置失败")
        row = up.data[0]
        return {
            "task": enrich_task_for_task_center(row),
            "idempotent": False,
            "action": "reset_to_pending",
            "message": "已重置为 pending，可重新抓取与分析",
        }

    if status == "running":
        raise HTTPException(
            status_code=409,
            detail="任务执行中，无法重试；请等待结束或失败后再试",
        )
    if status == "success":
        raise HTTPException(
            status_code=409,
            detail="任务已成功，无需重试；如需重新跑请新建任务",
        )
    if status == "cancelled":
        raise HTTPException(
            status_code=409,
            detail="任务已取消，不支持重试",
        )

    raise HTTPException(status_code=400, detail=f"未知状态：{status!r}")
