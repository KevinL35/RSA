"""审计写入：失败不影响主业务。"""

from __future__ import annotations

import logging
from typing import Any

from supabase import Client

from .repo import insert_audit_log

log = logging.getLogger(__name__)


def audit_actor_name(username: str | None) -> str:
    s = (username or "").strip()
    return s[:128] if s else "unknown"


def try_record_audit(
    sb: Client | None,
    *,
    username: str,
    menu_key: str,
    message: str,
    detail: dict[str, Any] | None = None,
) -> None:
    if sb is None:
        return
    try:
        insert_audit_log(sb, username=username, menu_key=menu_key, message=message, detail=detail)
    except Exception:  # noqa: BLE001
        log.exception("audit_logs 写入失败（已忽略） menu_key=%s", menu_key)
