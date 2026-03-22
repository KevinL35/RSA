from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.rbac import get_rsa_role, get_rsa_username_optional, require_mutator_role
from app.integrations.supabase import require_supabase
from app.modules.audit_log.service import audit_actor_name, try_record_audit

from .guidance import format_compare_prerequisite_error
from .runs_repo import delete_compare_run, get_compare_run, insert_compare_run, list_compare_runs
from .service import build_product_compare

router = APIRouter(prefix="/api/v1/compare", tags=["compare"])


class CompareRunCreateBody(BaseModel):
    platform_a: str = Field(..., min_length=1)
    product_id_a: str = Field(..., min_length=1)
    platform_b: str = Field(..., min_length=1)
    product_id_b: str = Field(..., min_length=1)
    model_id: str | None = None
    model_label: str | None = None


@router.get("/products")
def compare_products(
    _rbac: Annotated[str, Depends(get_rsa_role)],
    platform_a: str = Query(..., description="商品 A 平台"),
    product_id_a: str = Query(..., description="商品 A 商品 ID"),
    platform_b: str = Query(..., description="商品 B 平台"),
    product_id_b: str = Query(..., description="商品 B 商品 ID"),
) -> dict:
    """TB-9/TB-10：双商品对比；缺数据时 400 含双语提示与任务中心引导。"""
    try:
        sb = require_supabase()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    try:
        raw = build_product_compare(
            sb,
            platform_a=platform_a,
            product_id_a=product_id_a,
            platform_b=platform_b,
            product_id_b=product_id_b,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Supabase 查询失败：{e!s}") from e

    if raw.get("_missing"):
        raise HTTPException(
            status_code=400,
            detail=format_compare_prerequisite_error(raw),
        )
    return raw


@router.get("/runs")
def list_compare_run_rows(
    _rbac: Annotated[str, Depends(get_rsa_role)],
    limit: int = Query(100, ge=1, le=200),
) -> dict:
    """对比分析历史列表（存 Supabase compare_runs）。"""
    try:
        sb = require_supabase()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    try:
        return {"items": list_compare_runs(sb, limit=limit)}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Supabase 查询失败：{e!s}") from e


@router.get("/runs/{run_id}")
def get_compare_run_row(
    run_id: UUID,
    _rbac: Annotated[str, Depends(get_rsa_role)],
) -> dict:
    try:
        sb = require_supabase()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    try:
        row = get_compare_run(sb, run_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Supabase 查询失败：{e!s}") from e
    if not row:
        raise HTTPException(status_code=404, detail="对比记录不存在")
    return row


@router.delete("/runs/{run_id}")
def delete_compare_run_row(
    run_id: UUID,
    _mutator: Annotated[str, Depends(require_mutator_role)],
    actor: Annotated[str | None, Depends(get_rsa_username_optional)] = None,
) -> dict:
    try:
        sb = require_supabase()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    try:
        ok = delete_compare_run(sb, run_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Supabase 删除失败：{e!s}") from e
    if not ok:
        raise HTTPException(status_code=404, detail="对比记录不存在")
    try_record_audit(
        sb,
        username=audit_actor_name(actor),
        menu_key="compare",
        message=f"删除对比记录 {run_id}",
        detail={"run_id": str(run_id)},
    )
    return {"ok": True}


@router.post("/runs")
def create_compare_run_row(
    body: CompareRunCreateBody,
    _mutator: Annotated[str, Depends(require_mutator_role)],
    created_by: Annotated[str | None, Depends(get_rsa_username_optional)] = None,
) -> dict:
    """执行双商品对比并写入 compare_runs；前置不满足时仍写入 failed 记录。"""
    try:
        sb = require_supabase()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    pa, pida = body.platform_a.strip(), body.product_id_a.strip()
    pb, pidb = body.platform_b.strip(), body.product_id_b.strip()
    creator = (created_by or "").strip() or "unknown"

    base_row: dict = {
        "platform_a": pa,
        "product_id_a": pida,
        "platform_b": pb,
        "product_id_b": pidb,
        "creator": creator,
        "model_id": body.model_id,
        "model_label": (body.model_label or "").strip() or "",
    }

    try:
        raw = build_product_compare(
            sb,
            platform_a=pa,
            product_id_a=pida,
            platform_b=pb,
            product_id_b=pidb,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Supabase 查询失败：{e!s}") from e

    if raw.get("_missing"):
        detail = format_compare_prerequisite_error(raw)
        msgs = detail.get("messages") if isinstance(detail.get("messages"), dict) else {}
        err_zh = str(msgs.get("zh_CN") or detail.get("message") or "对比前置条件不满足")
        try:
            inserted = insert_compare_run(
                sb,
                {
                    **base_row,
                    "status": "failed",
                    "error_message": err_zh[:8000],
                    "result": None,
                },
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"写入对比记录失败：{e!s}") from e
        rid = str(inserted["id"])
        try_record_audit(
            sb,
            username=audit_actor_name(created_by),
            menu_key="compare",
            message=f"添加对比记录（失败）{pa}/{pida} vs {pb}/{pidb}",
            detail={"run_id": rid, "status": "failed"},
        )
        return {
            "id": rid,
            "status": "failed",
            "error_message": err_zh,
        }

    try:
        inserted = insert_compare_run(
            sb,
            {
                **base_row,
                "status": "success",
                "error_message": None,
                "result": raw,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"写入对比记录失败：{e!s}") from e
    rid = str(inserted["id"])
    try_record_audit(
        sb,
        username=audit_actor_name(created_by),
        menu_key="compare",
        message=f"添加对比记录（成功）{pa}/{pida} vs {pb}/{pidb}",
        detail={"run_id": rid, "status": "success"},
    )
    return {
        "id": rid,
        "status": "success",
        "error_message": None,
    }
