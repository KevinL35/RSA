from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .verticals import VERTICAL_IDS

SIX_WAY_DIMENSION_ORDER: tuple[str, ...] = (
    "pros",
    "cons",
    "return_reasons",
    "purchase_motivation",
    "user_expectation",
    "usage_scenario",
)


def _repo_root() -> Path:
    # apps/api/app/modules/dictionary/taxonomy_yaml.py -> parents[5] = repo root
    return Path(__file__).resolve().parents[5]


def _configs_dir() -> Path:
    return _repo_root() / "ml" / "configs"


def _load_yaml_entries(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not raw or not isinstance(raw, dict):
        return []
    entries = raw.get("entries")
    if not isinstance(entries, list):
        return []
    out: list[dict[str, Any]] = []
    for e in entries:
        if isinstance(e, dict) and e.get("dimension_6way") and e.get("canonical"):
            out.append(e)
    return out


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


def load_merged_entries_for_vertical(vertical_id: str) -> list[dict[str, Any]]:
    """general：仅种子；其他垂直：种子 + 垂直 overlay 合并。"""
    vid = vertical_id.strip()
    if vid not in VERTICAL_IDS:
        raise ValueError(f"未知 vertical：{vertical_id!r}")

    seed_path = _configs_dir() / "taxonomy_dictionary_seed_v1.yaml"
    base = _load_yaml_entries(seed_path)

    if vid == "general":
        return base

    overlay_name = f"taxonomy_dictionary_{vid}_overlay_v1.yaml"
    overlay_path = _configs_dir() / overlay_name
    overlay = _load_yaml_entries(overlay_path)
    return merge_entries(base, overlay)


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
