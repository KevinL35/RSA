"""构建审核词条结构；已生效写入 Supabase `taxonomy_entries`（overlay 层）。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from supabase import Client

from .taxonomy_db import bulk_upsert_overlay_entries


def build_dictionary_review_entry(
    *,
    dimension_6way: str,
    canonical: str,
    aliases: list[str],
    actor_username: str | None,
    batch_id: str | None,
    source_topic_id: str | None,
    weight: float = 1.0,
    priority: int = 50,
    entry_source: str = "dictionary_review",
) -> dict[str, Any]:
    dim = dimension_6way.strip().lower()
    can = canonical.strip()
    if len(can) < 2:
        raise ValueError("canonical 至少 2 字符")
    als = [str(a).strip() for a in aliases if str(a).strip()]
    iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        w = float(weight)
    except (TypeError, ValueError):
        w = 1.0
    try:
        pr = int(priority)
    except (TypeError, ValueError):
        pr = 50
    return {
        "dimension_6way": dim,
        "canonical": can,
        "aliases": als,
        "weight": w,
        "priority": pr,
        "entry_source": entry_source,
        "provenance": {
            "batch_id": batch_id,
            "source_topic_id": source_topic_id,
            "reviewer": (actor_username or "").strip() or "unknown",
            "reviewed_at": iso,
        },
    }


def merge_entry_into_vertical_overlay(
    sb: Client,
    vertical_id: str,
    entry: dict[str, Any],
) -> dict[str, Any]:
    """写入单个 vertical 的 overlay（Supabase），返回 { vertical_id, path, version, entry_count }。"""
    return merge_entries_bulk_into_vertical_overlay(sb, vertical_id, [entry])


def merge_entries_bulk_into_vertical_overlay(
    sb: Client,
    vertical_id: str,
    entries: list[dict[str, Any]],
) -> dict[str, Any]:
    """批量 upsert 至 overlay 层。"""
    return bulk_upsert_overlay_entries(sb, vertical_id, entries)
