from __future__ import annotations

from datetime import datetime
from typing import Any

from supabase import Client


def parse_status_filter(raw: str | None) -> list[str] | None:
    if not raw or not raw.strip():
        return None
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    allowed = {"pending", "running", "success", "failed", "cancelled"}
    bad = [p for p in parts if p not in allowed]
    if bad:
        raise ValueError(f"无效 status：{bad}，允许：{', '.join(sorted(allowed))}")
    return parts


def enrich_task_for_task_center(row: dict[str, Any]) -> dict[str, Any]:
    """TB-6：失败任务附带结构化 error 块。"""
    out = dict(row)
    if row.get("status") == "failed":
        out["error"] = {
            "stage": row.get("failure_stage"),
            "code": row.get("error_code"),
            "message": row.get("error_message"),
        }
    else:
        out["error"] = None
    return out


def list_insight_tasks_filtered(
    sb: Client,
    *,
    task_type: str | None,
    status_csv: str | None,
    created_after: str | None,
    created_before: str | None,
    limit: int,
) -> dict[str, Any]:
    if task_type is not None and task_type.strip() and task_type.strip() != "insight":
        raise ValueError(
            f"无效 task_type：{task_type!r}，当前仅支持 insight（或省略）"
        )

    statuses = parse_status_filter(status_csv)

    def _check_iso(label: str, s: str) -> None:
        try:
            datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError as e:
            raise ValueError(f"{label} 不是合法 ISO8601 时间：{s!r}") from e

    if created_after:
        _check_iso("created_after", created_after)
    if created_before:
        _check_iso("created_before", created_before)

    q = sb.table("insight_tasks").select("*")
    if statuses:
        q = q.in_("status", statuses)
    if created_after:
        q = q.gte("created_at", created_after)
    if created_before:
        q = q.lte("created_at", created_before)

    res = q.order("created_at", desc=True).limit(limit).execute()
    items = [enrich_task_for_task_center(r) for r in (res.data or [])]

    return {
        "items": items,
        "filters_applied": {
            "task_type": task_type.strip() if task_type and task_type.strip() else "insight",
            "status": statuses,
            "created_after": created_after,
            "created_before": created_before,
            "limit": limit,
        },
    }
