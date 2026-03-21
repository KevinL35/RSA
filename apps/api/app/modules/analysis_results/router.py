from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.rbac import get_rsa_role
from app.integrations.supabase import require_supabase

_DIMS = frozenset(
    {
        "pros",
        "cons",
        "return_reasons",
        "purchase_motivation",
        "user_expectation",
        "usage_scenario",
    }
)

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis-results"])


@router.get("/by-product")
def list_dimension_hits_by_product(
    _rbac: Annotated[str, Depends(get_rsa_role)],
    platform: str = Query(min_length=1, max_length=64),
    product_id: str = Query(min_length=1, max_length=256),
    dimension: str | None = Query(
        default=None,
        description="可选：pros|cons|return_reasons|purchase_motivation|user_expectation|usage_scenario",
    ),
) -> dict:
    """TB-4：按商品（+可选维度）检索六维命中行，并附带原评论正文便于证据追溯。"""
    try:
        sb = require_supabase()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    q = (
        sb.table("review_dimension_analysis")
        .select("*")
        .eq("platform", platform.strip())
        .eq("product_id", product_id.strip())
    )
    if dimension:
        ds = dimension.strip()
        if ds not in _DIMS:
            raise HTTPException(
                status_code=400,
                detail=f"无效 dimension，允许值：{', '.join(sorted(_DIMS))}",
            )
        q = q.eq("dimension", ds)
    try:
        res = q.order("created_at", desc=True).limit(500).execute()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Supabase 查询失败：{e!s}") from e

    hits = res.data or []
    rids = list({str(h["review_id"]) for h in hits if h.get("review_id")})
    review_map: dict[str, dict] = {}
    if rids:
        try:
            rv = sb.table("reviews").select("id,raw_text,title,rating").in_("id", rids).execute()
            for row in rv.data or []:
                review_map[str(row["id"])] = row
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=502, detail=f"Supabase 查询评论失败：{e!s}") from e

    enriched = []
    for h in hits:
        rid = str(h.get("review_id", ""))
        enriched.append({**h, "review": review_map.get(rid)})

    return {
        "platform": platform.strip(),
        "product_id": product_id.strip(),
        "dimension_filter": dimension.strip() if dimension else None,
        "items": enriched,
    }
