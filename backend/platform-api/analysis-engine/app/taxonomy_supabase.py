"""从 Supabase taxonomy_entries 拉取 seed/overlay，与 backend/platform-api 合并语义一致。"""

from __future__ import annotations

import os
from typing import Any

from supabase import Client, create_client


def get_supabase_optional() -> Client | None:
    url = (os.environ.get("SUPABASE_URL") or "").strip()
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not url or not key:
        return None
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
    try:
        res = sb.table("taxonomy_entries").select("*").eq("source_layer", "seed").execute()
    except Exception:
        return []
    rows = res.data or []
    return [row_to_entry(r) for r in rows if isinstance(r, dict)]


def fetch_overlay_rows(sb: Client, vertical_id: str) -> list[dict[str, Any]]:
    vid = vertical_id.strip()
    try:
        res = (
            sb.table("taxonomy_entries")
            .select("*")
            .eq("source_layer", "overlay")
            .eq("dictionary_vertical_id", vid)
            .execute()
        )
    except Exception:
        return []
    rows = res.data or []
    return [row_to_entry(r) for r in rows if isinstance(r, dict)]
