"""离线脚本：Supabase taxonomy_entries 读写（overlay 全量替换、导出快照）。"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from supabase import Client, create_client


def get_supabase_client() -> Client:
    url = (os.environ.get("SUPABASE_URL") or "").strip()
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not url or not key:
        raise RuntimeError("需要环境变量 SUPABASE_URL 与 SUPABASE_SERVICE_ROLE_KEY")
    return create_client(url, key)


def row_to_entry(row: dict[str, Any]) -> dict[str, Any]:
    als = row.get("aliases")
    if not isinstance(als, list):
        als = []
    prov = row.get("provenance")
    if prov is not None and not isinstance(prov, dict):
        prov = None
    return {
        "dimension_6way": str(row.get("dimension_6way") or "").strip().lower(),
        "canonical": str(row.get("canonical") or "").strip(),
        "aliases": [str(a).strip() for a in als if str(a).strip()],
        "weight": float(row.get("weight") if row.get("weight") is not None else 1.0),
        "priority": int(row.get("priority") if row.get("priority") is not None else 50),
        "entry_source": row.get("entry_source"),
        "provenance": prov,
    }


def fetch_seed_rows(sb: Client) -> list[dict[str, Any]]:
    res = sb.table("taxonomy_entries").select("*").eq("source_layer", "seed").execute()
    rows = res.data or []
    return [row_to_entry(r) for r in rows if isinstance(r, dict)]


def fetch_overlay_rows(sb: Client, vertical_id: str) -> list[dict[str, Any]]:
    vid = vertical_id.strip()
    res = (
        sb.table("taxonomy_entries")
        .select("*")
        .eq("source_layer", "overlay")
        .eq("dictionary_vertical_id", vid)
        .execute()
    )
    rows = res.data or []
    return [row_to_entry(r) for r in rows if isinstance(r, dict)]


def _canonical_norm(canonical: str) -> str:
    return str(canonical or "").strip().lower()


def overlay_entry_to_insert_row(vertical_id: str, e: dict[str, Any]) -> dict[str, Any]:
    dim = str(e.get("dimension_6way") or "").strip().lower()
    can = str(e.get("canonical") or "").strip()
    als = e.get("aliases")
    if not isinstance(als, list):
        als = []
    als = [str(a).strip() for a in als if str(a).strip()]
    now = datetime.now(timezone.utc).isoformat()
    prov = e.get("provenance")
    if prov is not None and not isinstance(prov, dict):
        prov = None
    return {
        "source_layer": "overlay",
        "dictionary_vertical_id": vertical_id.strip(),
        "dimension_6way": dim,
        "canonical": can,
        "canonical_norm": _canonical_norm(can),
        "aliases": als,
        "weight": float(e.get("weight") if e.get("weight") is not None else 1.0),
        "priority": int(e.get("priority") if e.get("priority") is not None else 50),
        "entry_source": e.get("entry_source"),
        "provenance": prov,
        "created_at": now,
        "updated_at": now,
    }


def replace_vertical_overlay(sb: Client, vertical_id: str, merged_entries: list[dict[str, Any]]) -> None:
    """删除该 vertical 的全部 overlay 行，再插入 merged_entries（全量替换）。"""
    vid = vertical_id.strip()
    sb.table("taxonomy_entries").delete().eq("source_layer", "overlay").eq("dictionary_vertical_id", vid).execute()
    for e in merged_entries:
        row = overlay_entry_to_insert_row(vid, e)
        sb.table("taxonomy_entries").insert(row).execute()


def export_overlay_document(sb: Client, vertical_id: str) -> dict[str, Any]:
    entries = fetch_overlay_rows(sb, vertical_id)
    return {
        "version": "1.0.0",
        "taxonomy_id": f"snapshot-{vertical_id}-overlay",
        "description": "Exported from Supabase taxonomy_entries (overlay).",
        "entries": entries,
    }
