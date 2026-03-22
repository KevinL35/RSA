"""
按 dictionary_vertical_id 合并 seed + overlay；**仅**从 Supabase 读取，与 apps/api taxonomy_yaml 口径一致。
未配置 Supabase 或 seed 为空时会报错（请用 ml/fixtures/taxonomy/ + seed 脚本初始化库表）。
"""

from __future__ import annotations

from typing import Any

from .taxonomy_supabase import fetch_overlay_rows, fetch_seed_rows, get_supabase_optional

_KNOWN_VERTICALS = frozenset({"general", "electronics"})


def _entry_key(e: dict[str, Any]) -> tuple[str, str]:
    dim = str(e.get("dimension_6way", "")).strip().lower()
    can = str(e.get("canonical", "")).strip().lower()
    return (dim, can)


def _merge_entries(base: list[dict[str, Any]], overlay: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for e in base:
        by_key[_entry_key(e)] = dict(e)
    for e in overlay:
        by_key[_entry_key(e)] = dict(e)
    return list(by_key.values())


def load_merged_taxonomy_dict(vertical_id: str | None) -> dict[str, Any]:
    sb = get_supabase_optional()
    if sb is None:
        raise RuntimeError(
            "词典仅从 Supabase 读取：请为 rsa-model-api 配置环境变量 SUPABASE_URL 与 SUPABASE_SERVICE_ROLE_KEY。"
        )
    vid = (vertical_id or "general").strip() or "general"
    if vid not in _KNOWN_VERTICALS:
        vid = "general"
    try:
        db_seed = fetch_seed_rows(sb)
        db_overlay = fetch_overlay_rows(sb, vid)
    except Exception as e:
        raise RuntimeError(f"读取 taxonomy_entries 失败：{e}") from e
    if not db_seed:
        raise RuntimeError(
            "Supabase taxonomy_entries 中 seed 为空。请执行 scripts/seed_taxonomy_yaml_to_supabase.py "
            "（YAML 源位于 ml/fixtures/taxonomy/）。"
        )
    return {"entries": _merge_entries(db_seed, db_overlay)}
