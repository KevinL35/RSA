"""已生效词典的 Supabase 读写；与 taxonomy_yaml 合并规则一致。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from supabase import Client

from .taxonomy_yaml import merge_entries
from .verticals import VERTICAL_IDS


def _canonical_norm(canonical: str) -> str:
    return str(canonical or "").strip().lower()


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


def count_overlay_entries(sb: Client, vertical_id: str) -> int:
    return len(fetch_overlay_rows(sb, vertical_id))


def _overlay_row_payload(vertical_id: str, entry: dict[str, Any]) -> dict[str, Any]:
    dim = str(entry.get("dimension_6way") or "").strip().lower()
    can = str(entry.get("canonical") or "").strip()
    als = entry.get("aliases")
    if not isinstance(als, list):
        als = []
    als = [str(a).strip() for a in als if str(a).strip()]
    now = datetime.now(timezone.utc).isoformat()
    prov = entry.get("provenance")
    if prov is not None and not isinstance(prov, dict):
        prov = None
    return {
        "source_layer": "overlay",
        "dictionary_vertical_id": vertical_id.strip(),
        "dimension_6way": dim,
        "canonical": can,
        "canonical_norm": _canonical_norm(can),
        "aliases": als,
        "weight": float(entry.get("weight") if entry.get("weight") is not None else 1.0),
        "priority": int(entry.get("priority") if entry.get("priority") is not None else 50),
        "entry_source": entry.get("entry_source"),
        "provenance": prov,
        "updated_at": now,
    }


def upsert_overlay_entry(sb: Client, vertical_id: str, entry: dict[str, Any]) -> None:
    vid = vertical_id.strip()
    if vid not in VERTICAL_IDS:
        raise ValueError(f"无效 vertical_id：{vertical_id!r}")
    payload = _overlay_row_payload(vid, entry)
    dim = payload["dimension_6way"]
    cn = payload["canonical_norm"]
    existing = (
        sb.table("taxonomy_entries")
        .select("id")
        .eq("source_layer", "overlay")
        .eq("dictionary_vertical_id", vid)
        .eq("dimension_6way", dim)
        .eq("canonical_norm", cn)
        .limit(1)
        .execute()
    )
    rows = existing.data or []
    if rows:
        sb.table("taxonomy_entries").update(payload).eq("id", str(rows[0]["id"])).execute()
    else:
        payload["created_at"] = payload["updated_at"]
        sb.table("taxonomy_entries").insert(payload).execute()


def bulk_upsert_overlay_entries(sb: Client, vertical_id: str, entries: list[dict[str, Any]]) -> dict[str, Any]:
    vid = vertical_id.strip()
    if vid not in VERTICAL_IDS:
        raise ValueError(f"无效 vertical_id：{vertical_id!r}")
    if not entries:
        raise ValueError("entries 不能为空")
    for e in entries:
        upsert_overlay_entry(sb, vid, e)
    n = count_overlay_entries(sb, vid)
    return {
        "vertical_id": vid,
        "path": "supabase://taxonomy_entries",
        "version": "db",
        "entry_count": n,
    }
