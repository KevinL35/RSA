"""
按 dictionary_vertical_id 合并 seed + overlay，与 apps/api taxonomy_yaml 口径一致。
仓库根目录下 ml/configs/；未知 vertical 时回退 general。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .taxonomy_supabase import fetch_overlay_rows, fetch_seed_rows, get_supabase_optional

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CONFIGS_DIR = _REPO_ROOT / "ml" / "configs"
_SEED_PATH = _CONFIGS_DIR / "taxonomy_dictionary_seed_v1.yaml"

_KNOWN_VERTICALS = frozenset({"general", "electronics"})


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


def _merge_entries(base: list[dict[str, Any]], overlay: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for e in base:
        by_key[_entry_key(e)] = dict(e)
    for e in overlay:
        by_key[_entry_key(e)] = dict(e)
    return list(by_key.values())


def load_merged_taxonomy_dict(vertical_id: str | None) -> dict[str, Any]:
    vid = (vertical_id or "general").strip() or "general"
    if vid not in _KNOWN_VERTICALS:
        vid = "general"
    yaml_seed = _load_yaml_entries(_SEED_PATH)
    if vid == "general":
        overlay_path = _CONFIGS_DIR / "taxonomy_dictionary_general_overlay_v1.yaml"
    else:
        overlay_path = _CONFIGS_DIR / f"taxonomy_dictionary_{vid}_overlay_v1.yaml"
    yaml_overlay = _load_yaml_entries(overlay_path)

    sb = get_supabase_optional()
    if sb is None:
        return {"entries": _merge_entries(yaml_seed, yaml_overlay)}
    try:
        db_seed = fetch_seed_rows(sb)
        db_overlay = fetch_overlay_rows(sb, vid)
    except Exception:
        db_seed, db_overlay = [], []
    seed = db_seed if db_seed else yaml_seed
    overlay = db_overlay if db_overlay else yaml_overlay
    return {"entries": _merge_entries(seed, overlay)}
