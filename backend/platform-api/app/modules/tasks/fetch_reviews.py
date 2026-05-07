from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from supabase import Client

from app.core.config import get_settings
from app.integrations.review_provider import ReviewProviderError, fetch_reviews_normalized
from app.modules.tasks import state_machine
from app.modules.tasks.listing import enrich_task_for_task_center

log = logging.getLogger("rsa.fetch_reviews")


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
            detail="任务已失败：请先 POST /api/v1/insight-tasks/{id}/retry 重置为 pending，再抓取评论",
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
            .execute()
        )
        if not up.data:
            raise HTTPException(status_code=500, detail="无法将任务置为 running")
        task = up.data[0]

    settings = get_settings()
    try:
        normalized = fetch_reviews_normalized(platform, product_id, settings=settings)
    except ReviewProviderError as e:
        log.warning(
            "fetch_reviews failed task=%s platform=%s product_id=%s code=%s detail=%s",
            task_id,
            platform,
            product_id,
            e.code,
            (e.message or "")[:800],
        )
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

    if not normalized:
        log.warning(
            "fetch_reviews zero rows after provider ok task=%s platform=%s product_id=%s "
            "(响应成功但无可入库评论，可能是 ASIN/站点无评论或解析字段不匹配)",
            task_id,
            platform,
            product_id,
        )

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

    _spawn_product_snapshot_async(sb, task_id, platform, product_id, settings)

    fresh = (
        sb.table("insight_tasks")
        .select("*")
        .eq("id", str(task_id))
        .limit(1)
        .execute()
    )
    task_row = (fresh.data or [task])[0]
    return {
        "task": enrich_task_for_task_center(task_row),
        "reviews_inserted": len(insert_rows),
    }


def _spawn_product_snapshot_async(
    sb: Client,
    task_id: UUID,
    platform: str,
    product_id: str,
    settings: object,
) -> None:
    mode = (getattr(settings, "review_provider_mode", "") or "http").strip().lower()
    if (
        mode != "pangolin"
        or platform.strip().lower() != "amazon"
        or not getattr(settings, "pangolin_fetch_product_detail", False)
        or getattr(settings, "review_provider_mock", False)
    ):
        return

    def _runner() -> None:
        try:
            from app.integrations.review_provider.pangolin_product import (
                try_fetch_pangolin_product_snapshot_optional,
            )

            product_snapshot = try_fetch_pangolin_product_snapshot_optional(
                platform,
                product_id,
                settings=settings,  # type: ignore[arg-type]
            )
            if not product_snapshot:
                return
            sb.table("insight_tasks").update(
                {
                    "product_snapshot": product_snapshot,
                    "updated_at": _utc_now_iso(),
                }
            ).eq("id", str(task_id)).execute()
        except Exception as e:
            log.warning("product snapshot async fetch failed for task=%s: %s", task_id, e)

    threading.Thread(
        target=_runner,
        name=f"product-snapshot-{str(task_id)[:8]}",
        daemon=True,
    ).start()
