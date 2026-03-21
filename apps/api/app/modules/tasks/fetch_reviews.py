from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from supabase import Client

from app.core.config import get_settings
from app.integrations.review_provider import ReviewProviderError, fetch_reviews_normalized
from app.modules.tasks import state_machine


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_fetch_reviews_for_task(sb: Client, task_id: UUID) -> dict:
    """将任务置为 running（若原为 pending）、抓取评论写入 reviews；失败则任务 failed（failure_stage=fetch）。"""
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
    if status in ("success", "cancelled"):
        raise HTTPException(
            status_code=409,
            detail=f"任务状态为 {status}，不可抓取评论",
        )
    if status == "failed":
        raise HTTPException(
            status_code=400,
            detail="任务已失败：请使用 PATCH 将状态改为 pending 后再抓取",
        )

    platform = task["platform"]
    product_id = task["product_id"]

    if status == "pending":
        try:
            state_machine.assert_valid_transition("pending", "running")
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
                }
            )
            .eq("id", str(task_id))
            .select("*")
            .execute()
        )
        if not up.data:
            raise HTTPException(status_code=500, detail="无法将任务置为 running")
        task = up.data[0]

    settings = get_settings()
    try:
        normalized = fetch_reviews_normalized(platform, product_id, settings=settings)
    except ReviewProviderError as e:
        sb.table("insight_tasks").update(
            {
                "status": "failed",
                "updated_at": _utc_now_iso(),
                "error_code": e.code,
                "error_message": e.message[:4000],
                "failure_stage": "fetch",
            }
        ).eq("id", str(task_id)).execute()
        raise HTTPException(
            status_code=502,
            detail=f"{e.code}: {e.message}",
        ) from e

    sb.table("reviews").delete().eq("insight_task_id", str(task_id)).execute()

    insert_rows: list[dict] = []
    for r in normalized:
        insert_rows.append(
            {
                "insight_task_id": str(task_id),
                "platform": platform,
                "product_id": product_id,
                "external_review_id": r.get("external_review_id"),
                "raw_text": r["raw_text"],
                "title": r.get("title"),
                "rating": r.get("rating"),
                "sku": r.get("sku"),
                "reviewed_at": r.get("reviewed_at"),
                "lang": r.get("lang"),
                "extra": r.get("extra"),
            }
        )

    if insert_rows:
        sb.table("reviews").insert(insert_rows).execute()

    fresh = (
        sb.table("insight_tasks")
        .select("*")
        .eq("id", str(task_id))
        .limit(1)
        .execute()
    )
    task_row = (fresh.data or [task])[0]
    return {"task": task_row, "reviews_inserted": len(insert_rows)}
