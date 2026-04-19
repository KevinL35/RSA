from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from supabase import Client

SIX_WAY_DIMENSION_ORDER: tuple[str, ...] = (
    "pros",
    "cons",
    "return_reasons",
    "purchase_motivation",
    "user_expectation",
    "usage_scenario",
)


def _entry_key(e: dict[str, Any]) -> tuple[str, str]:
    dim = str(e.get("dimension_6way", "")).strip().lower()
    can = str(e.get("canonical", "")).strip().lower()
    return (dim, can)


def merge_entries(base: list[dict[str, Any]], overlay: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """overlay 覆盖 base 中同 (dimension_6way, canonical) 的词条。"""
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for e in base:
        by_key[_entry_key(e)] = dict(e)
    for e in overlay:
        by_key[_entry_key(e)] = dict(e)
    return list(by_key.values())


def load_merged_entries_for_vertical(
    vertical_id: str,
    sb: "Client | None" = None,
) -> list[dict[str, Any]]:
    """从 Supabase `taxonomy_entries` 合并 seed + 指定 vertical 的 overlay。seed 可为空，此时结果仅为 overlay。"""
    from . import taxonomy_db as _taxonomy_db
    from .verticals import VERTICAL_IDS

    vid = vertical_id.strip()
    if vid not in VERTICAL_IDS:
        raise ValueError(f"未知 vertical：{vertical_id!r}")
    if sb is None:
        raise ValueError(
            "合并词典已改为仅读取 Supabase：请传入 Supabase Client（需配置 SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY）。"
        )
    try:
        db_seed = _taxonomy_db.fetch_seed_rows(sb)
        db_overlay = _taxonomy_db.fetch_overlay_rows(sb, vid)
    except Exception as e:
        raise ValueError(f"读取 taxonomy_entries 失败：{e!s}") from e
    return merge_entries(db_seed, db_overlay)


def group_by_dimension(entries: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {d: [] for d in SIX_WAY_DIMENSION_ORDER}
    for e in entries:
        dim = str(e.get("dimension_6way", "")).strip().lower()
        if dim not in groups:
            groups[dim] = []
        groups[dim].append(e)
    for dim in groups:
        groups[dim].sort(key=lambda x: (-int(x.get("priority") or 0), str(x.get("canonical", ""))))
    return groups
