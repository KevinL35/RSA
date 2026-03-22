"""对比分析记录：Supabase compare_runs 表 CRUD。"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from supabase import Client


def list_compare_runs(sb: Client, *, limit: int) -> list[dict[str, Any]]:
    lim = max(1, min(limit, 200))
    res = (
        sb.table("compare_runs")
        .select(
            "id,platform_a,product_id_a,platform_b,product_id_b,creator,created_at,"
            "model_id,model_label,status,error_message"
        )
        .order("created_at", desc=True)
        .limit(lim)
        .execute()
    )
    return list(res.data or [])


def get_compare_run(sb: Client, run_id: UUID) -> dict[str, Any] | None:
    res = sb.table("compare_runs").select("*").eq("id", str(run_id)).limit(1).execute()
    rows = res.data or []
    return rows[0] if rows else None


def delete_compare_run(sb: Client, run_id: UUID) -> bool:
    cur = sb.table("compare_runs").select("id").eq("id", str(run_id)).limit(1).execute()
    if not (cur.data or []):
        return False
    sb.table("compare_runs").delete().eq("id", str(run_id)).execute()
    return True


def insert_compare_run(sb: Client, row: dict[str, Any]) -> dict[str, Any]:
    res = sb.table("compare_runs").insert(row).execute()
    data = res.data or []
    if not data:
        raise RuntimeError("插入 compare_runs 后未返回数据")
    return data[0]
