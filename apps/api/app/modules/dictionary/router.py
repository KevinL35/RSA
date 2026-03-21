from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.rbac import get_rsa_role, get_rsa_username_optional, require_mutator_role
from app.integrations.supabase import require_supabase
from app.modules.audit_log.service import audit_actor_name, try_record_audit
from supabase import Client

from .taxonomy_yaml import SIX_WAY_DIMENSION_ORDER, group_by_dimension, load_merged_entries_for_vertical
from .verticals import DICTIONARY_VERTICALS, assert_valid_vertical_id

router = APIRouter(prefix="/api/v1/dictionary", tags=["dictionary"])


@router.get("/verticals")
def list_dictionary_verticals(
    _rbac: Annotated[str, Depends(get_rsa_role)],
) -> dict:
    """一级词典垂直列表（类目），供洞察任务与词典管理页选择。"""
    return {
        "items": list(DICTIONARY_VERTICALS),
        "dimension_order": list(SIX_WAY_DIMENSION_ORDER),
    }


@router.get("/taxonomy-preview")
def get_taxonomy_preview(
    _rbac: Annotated[str, Depends(get_rsa_role)],
    vertical_id: str = Query(..., description="词典垂直 id，如 general / electronics"),
) -> dict:
    """按垂直返回合并后的词条，按六维分组（只读预览，供词典管理 UI）。"""
    try:
        vid = assert_valid_vertical_id(vertical_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    try:
        entries = load_merged_entries_for_vertical(vid)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"读取词典配置失败：{e!s}") from e

    grouped = group_by_dimension(entries)
    return {
        "vertical_id": vid,
        "entry_count": len(entries),
        "dimension_order": list(SIX_WAY_DIMENSION_ORDER),
        "dimensions": {
            dim: {
                "key": dim,
                "count": len(grouped.get(dim, [])),
                "entries": grouped.get(dim, []),
            }
            for dim in SIX_WAY_DIMENSION_ORDER
        },
    }


class RejectSynonymBody(BaseModel):
    vertical_id: str = Field(min_length=1, max_length=64)
    dimension_6way: str = Field(min_length=1, max_length=64)
    canonical: str = Field(min_length=1, max_length=512)
    alias: str = Field(min_length=1, max_length=512)


@router.post("/reject-synonym")
def post_reject_synonym(
    body: RejectSynonymBody,
    _rbac: Annotated[str, Depends(require_mutator_role)],
    actor: Annotated[str | None, Depends(get_rsa_username_optional)] = None,
    sb: Client = Depends(require_supabase),
) -> dict:
    """记录「同义词与关键词不匹配」的驳回意向，后续接入痛点审核队列与词典版本。"""
    try:
        assert_valid_vertical_id(body.vertical_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    dim = body.dimension_6way.strip().lower()
    if dim not in SIX_WAY_DIMENSION_ORDER:
        raise HTTPException(
            status_code=400,
            detail=f"无效 dimension_6way：{body.dimension_6way!r}",
        )
    try_record_audit(
        sb,
        username=audit_actor_name(actor),
        menu_key="dictionary",
        message=f"驳回同义词：{body.canonical.strip()} ↔ {body.alias.strip()}",
        detail={
            "vertical_id": body.vertical_id.strip(),
            "dimension_6way": dim,
            "canonical": body.canonical.strip(),
            "alias": body.alias.strip(),
        },
    )
    return {
        "ok": True,
        "queued": True,
        "vertical_id": body.vertical_id.strip(),
        "dimension_6way": dim,
        "canonical": body.canonical.strip(),
        "alias": body.alias.strip(),
    }
