"""audit_logs 表读写。"""

from __future__ import annotations

from typing import Any

from supabase import Client


def insert_audit_log(
    sb: Client,
    *,
    username: str,
    menu_key: str,
    message: str,
    detail: dict[str, Any] | None,
) -> None:
    row: dict[str, Any] = {
        "username": (username or "").strip()[:256] or "unknown",
        "menu_key": (menu_key or "").strip()[:128] or "unknown",
        "message": (message or "").strip()[:8000] or "—",
        "detail": detail,
    }
    sb.table("audit_logs").insert(row).execute()


def list_audit_logs(sb: Client, *, limit: int, offset: int) -> tuple[list[dict[str, Any]], int]:
    lim = max(1, min(limit, 200))
    off = max(0, offset)
    res = (
        sb.table("audit_logs")
        .select("id,username,menu_key,message,detail,created_at", count="exact")
        .order("created_at", desc=True)
        .range(off, off + lim - 1)
        .execute()
    )
    rows = list(res.data or [])
    total = res.count if isinstance(res.count, int) else len(rows)
    return rows, total
