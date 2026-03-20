from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.integrations.supabase import require_supabase

router = APIRouter(prefix="/api/v1/insight-tasks", tags=["insight-tasks"])

ALLOWED_STATUS = {"pending", "running", "success", "failed", "cancelled"}


class InsightTaskCreate(BaseModel):
    platform: str = Field(min_length=1, max_length=64)
    product_id: str = Field(min_length=1, max_length=256)
    analysis_provider_id: str | None = Field(default=None, max_length=128)


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
