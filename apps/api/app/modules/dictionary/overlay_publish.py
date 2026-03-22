"""构建审核词条结构；已生效写入 Supabase `taxonomy_entries`（overlay 层）。YAML 工具仍供 TA-10 等离线脚本使用。"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from supabase import Client

from .taxonomy_db import bulk_upsert_overlay_entries
from .taxonomy_yaml import merge_entries
from .verticals import VERTICAL_IDS


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _configs_dir() -> Path:
    return _repo_root() / "ml" / "configs"


def overlay_yaml_path(vertical_id: str) -> Path:
    vid = vertical_id.strip()
    if vid == "general":
        return _configs_dir() / "taxonomy_dictionary_general_overlay_v1.yaml"
    return _configs_dir() / f"taxonomy_dictionary_{vid}_overlay_v1.yaml"


def load_overlay_document(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "version": "1.0.0",
            "taxonomy_id": f"taxonomy-{path.stem}",
            "description": "",
            "entries": [],
        }
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid taxonomy yaml (not dict): {path}")
    entries = raw.get("entries")
    if entries is None:
        raw["entries"] = []
    elif not isinstance(entries, list):
        raise ValueError(f"Invalid entries in {path}")
    return raw


def write_overlay_document(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(
        doc,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )
    path.write_text(text, encoding="utf-8")


def bump_patch_version(v: str) -> str:
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)(.*)$", v.strip())
    if not m:
        return (v.strip() + ".1") if v.strip() else "1.0.1"
    major, minor, patch, rest = m.group(1), m.group(2), m.group(3), m.group(4) or ""
    return f"{major}.{minor}.{int(patch) + 1}{rest}"


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


def merge_entry_into_vertical_overlay_yaml(
    vertical_id: str,
    entry: dict[str, Any],
) -> dict[str, Any]:
    """离线：写入 ml/configs overlay YAML（TA-10 / 应急）。"""
    return merge_entries_bulk_into_vertical_overlay_yaml(vertical_id, [entry])


def merge_entries_bulk_into_vertical_overlay_yaml(
    vertical_id: str,
    entries: list[dict[str, Any]],
) -> dict[str, Any]:
    vid = vertical_id.strip()
    if vid not in VERTICAL_IDS:
        raise ValueError(f"无效 vertical_id：{vertical_id!r}")
    if not entries:
        raise ValueError("entries 不能为空")

    path = overlay_yaml_path(vid)
    doc = load_overlay_document(path)
    prev_entries = list(doc.get("entries") or [])
    merged_list = merge_entries(prev_entries, entries)
    doc["entries"] = merged_list
    doc["version"] = bump_patch_version(str(doc.get("version") or "1.0.0"))
    write_overlay_document(path, doc)
    return {
        "vertical_id": vid,
        "path": str(path.relative_to(_repo_root())),
        "version": doc["version"],
        "entry_count": len(merged_list),
    }
