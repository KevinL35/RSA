"""TB-13：固定模板 RBAC（admin / operator / readonly），与前端菜单一致。"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request

RSA_ROLE_HEADER = "X-RSA-Role"
VALID_ROLES = frozenset({"admin", "operator", "readonly"})

audit_log = logging.getLogger("rsa.audit")


def get_rsa_role(
    x_rsa_role: Annotated[str | None, Header(alias=RSA_ROLE_HEADER)] = None,
) -> str:
    """所有 /api/v1 业务接口需携带角色；与前端 localStorage `rsa_user_role` 对齐。"""
    if not x_rsa_role:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "MISSING_OR_INVALID_ROLE",
                "message": f"{RSA_ROLE_HEADER} header required: admin | operator | readonly",
            },
        )
    role = x_rsa_role.strip()
    if role not in VALID_ROLES:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "MISSING_OR_INVALID_ROLE",
                "message": f"Invalid role {role!r}; allowed: admin, operator, readonly",
            },
        )
    return role


def require_mutator_role(
    request: Request,
    role: Annotated[str, Depends(get_rsa_role)],
) -> str:
    """仅 admin / operator 可创建任务、拉取评论、分析、重试、PATCH 任务。"""
    if role == "readonly":
        audit_log.warning(
            "rbac_denied method=%s path=%s role=%s required=mutator",
            request.method,
            request.url.path,
            role,
        )
        raise HTTPException(
            status_code=403,
            detail={
                "code": "RBAC_FORBIDDEN",
                "message": "Read-only role cannot perform this action",
                "role": role,
                "required_roles": ["admin", "operator"],
            },
        )
    return role
