from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.rbac import get_rsa_role
from app.integrations.supabase import require_supabase

from .guidance import format_compare_prerequisite_error
from .service import build_product_compare

router = APIRouter(prefix="/api/v1/compare", tags=["compare"])


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
