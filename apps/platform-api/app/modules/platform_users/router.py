from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.core.rbac import get_rsa_role, get_rsa_username_optional
from app.integrations.supabase import get_supabase, require_supabase
from app.modules.audit_log.service import audit_actor_name, try_record_audit
from supabase import Client

from .constants import derive_api_role, normalize_menu_keys
from .schemas import (
    PlatformLoginBody,
    PlatformLoginResponse,
    PlatformUserCreateBody,
    PlatformUserListResponse,
    PlatformUserRow,
    PlatformUserUpdateBody,
)
from .service import create_user, delete_user, list_users, try_login, update_user

log = logging.getLogger(__name__)

auth_router = APIRouter(prefix="/api/v1/platform-auth", tags=["platform-auth"])
users_router = APIRouter(prefix="/api/v1/platform-users", tags=["platform-users"])


def _require_admin(role: Annotated[str, Depends(get_rsa_role)]) -> str:
    if role != "admin":
        raise HTTPException(
            status_code=403,
            detail={"code": "RBAC_FORBIDDEN", "message": "Admin role required"},
        )
    return role


@auth_router.post("/login", response_model=PlatformLoginResponse)
def platform_login(body: PlatformLoginBody) -> PlatformLoginResponse:
    sb = get_supabase()
    if sb is None:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "USER_STORE_UNAVAILABLE",
                "message": "User database not configured (Supabase)",
            },
        )
    result = try_login(sb, body.username, body.password)
    if not result:
        raise HTTPException(
            status_code=401,
            detail={"code": "INVALID_CREDENTIALS", "message": "Invalid username or password"},
        )
    row, token = result
    role = derive_api_role(row.menu_keys)
    try_record_audit(
        sb,
        username=row.username,
        menu_key="login",
        message="平台用户登录成功",
        detail=None,
    )
    return PlatformLoginResponse(
        username=row.username,
        role=role,
        menu_keys=row.menu_keys,
        token=token,
    )


@users_router.get("", response_model=PlatformUserListResponse)
def list_platform_users(
    _admin: str = Depends(_require_admin),
    sb: Client = Depends(require_supabase),
) -> PlatformUserListResponse:
    items = list_users(sb)
    return PlatformUserListResponse(items=items)


@users_router.post("", response_model=PlatformUserRow)
def create_platform_user(
    body: PlatformUserCreateBody,
    _admin: str = Depends(_require_admin),
    actor: Annotated[str | None, Depends(get_rsa_username_optional)] = None,
    sb: Client = Depends(require_supabase),
) -> PlatformUserRow:
    if not normalize_menu_keys(body.menu_keys):
        raise HTTPException(
            status_code=400,
            detail={"code": "MENU_KEYS_REQUIRED", "message": "Select at least one visible menu"},
        )
    try:
        row = create_user(
            sb,
            username=body.username,
            password=body.password,
            menu_keys=body.menu_keys,
            status=body.status,
        )
    except Exception as e:
        msg = str(e).lower()
        if "duplicate" in msg or "unique" in msg or "23505" in msg:
            raise HTTPException(
                status_code=409,
                detail={"code": "USERNAME_TAKEN", "message": "Username already exists"},
            ) from e
        log.exception("create_platform_user failed")
        raise HTTPException(status_code=500, detail={"code": "CREATE_FAILED", "message": str(e)}) from e
    try_record_audit(
        sb,
        username=audit_actor_name(actor),
        menu_key="account-permissions",
        message=f"创建平台账号 {row.username}",
        detail={"target_user_id": row.id},
    )
    return row


@users_router.patch("/{user_id}", response_model=PlatformUserRow)
def update_platform_user(
    user_id: str,
    body: PlatformUserUpdateBody,
    _admin: str = Depends(_require_admin),
    actor: Annotated[str | None, Depends(get_rsa_username_optional)] = None,
    sb: Client = Depends(require_supabase),
) -> PlatformUserRow:
    uid = user_id.strip()
    if not uid:
        raise HTTPException(status_code=400, detail="Invalid user id")
    if body.menu_keys is not None and not normalize_menu_keys(body.menu_keys):
        raise HTTPException(
            status_code=400,
            detail={"code": "MENU_KEYS_REQUIRED", "message": "Select at least one visible menu"},
        )
    pw = body.password if (body.password and body.password.strip()) else None
    try:
        row = update_user(
            sb,
            uid,
            username=body.username,
            password=pw,
            menu_keys=body.menu_keys,
            status=body.status,
        )
    except Exception as e:
        msg = str(e).lower()
        if "duplicate" in msg or "unique" in msg or "23505" in msg:
            raise HTTPException(
                status_code=409,
                detail={"code": "USERNAME_TAKEN", "message": "Username already exists"},
            ) from e
        log.exception("update_platform_user failed")
        raise HTTPException(status_code=500, detail={"code": "UPDATE_FAILED", "message": str(e)}) from e
    if not row:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "User not found"})
    try_record_audit(
        sb,
        username=audit_actor_name(actor),
        menu_key="account-permissions",
        message=f"更新平台账号 {row.username}",
        detail={"target_user_id": row.id},
    )
    return row


@users_router.delete("/{user_id}")
def delete_platform_user(
    user_id: str,
    _admin: str = Depends(_require_admin),
    actor: Annotated[str | None, Depends(get_rsa_username_optional)] = None,
    sb: Client = Depends(require_supabase),
) -> dict[str, bool]:
    uid = user_id.strip()
    if not uid:
        raise HTTPException(status_code=400, detail="Invalid user id")
    ok = delete_user(sb, uid)
    if not ok:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "User not found"})
    try_record_audit(
        sb,
        username=audit_actor_name(actor),
        menu_key="account-permissions",
        message=f"删除平台账号 id={uid}",
        detail={"target_user_id": uid},
    )
    return {"ok": True}
