from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.rbac import get_rsa_role
from app.integrations.supabase import require_supabase

from .repo import list_audit_logs

router = APIRouter(prefix="/api/v1/audit-logs", tags=["audit-logs"])


def _require_admin(role: Annotated[str, Depends(get_rsa_role)]) -> str:
    if role != "admin":
        raise HTTPException(
            status_code=403,
            detail={"code": "RBAC_FORBIDDEN", "message": "Admin role required"},
        )
    return role


@router.get("")
def list_audit_log_rows(
    _admin: Annotated[str, Depends(_require_admin)],
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    try:
        sb = require_supabase()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    try:
        items, total = list_audit_logs(sb, limit=limit, offset=offset)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"查询审计日志失败：{e!s}") from e
    return {"items": items, "total": total, "limit": limit, "offset": offset}
