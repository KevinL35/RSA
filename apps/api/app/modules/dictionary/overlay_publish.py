"""将词典审核通过的词条写入 ml/configs 下各垂直 overlay YAML（与 TA-10 脚本语义一致）。"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

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
) -> dict[str, Any]:
    dim = dimension_6way.strip().lower()
    can = canonical.strip()
    if len(can) < 2:
        raise ValueError("canonical 至少 2 字符")
    als = [str(a).strip() for a in aliases if str(a).strip()]
    iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "dimension_6way": dim,
        "canonical": can,
        "aliases": als,
        "weight": 1.0,
        "priority": 50,
        "entry_source": "dictionary_review",
        "provenance": {
            "batch_id": batch_id,
            "source_topic_id": source_topic_id,
            "reviewer": (actor_username or "").strip() or "unknown",
            "reviewed_at": iso,
        },
    }


def merge_entry_into_vertical_overlay(vertical_id: str, entry: dict[str, Any]) -> dict[str, Any]:
    """写入单个 vertical 的 overlay，返回 { vertical_id, path, version }。"""
    vid = vertical_id.strip()
    if vid not in VERTICAL_IDS:
        raise ValueError(f"无效 vertical_id：{vertical_id!r}")

    path = overlay_yaml_path(vid)
    doc = load_overlay_document(path)
    prev_entries = list(doc.get("entries") or [])
    merged_list = merge_entries(prev_entries, [entry])
    doc["entries"] = merged_list
    doc["version"] = bump_patch_version(str(doc.get("version") or "1.0.0"))
    write_overlay_document(path, doc)
    return {
        "vertical_id": vid,
        "path": str(path.relative_to(_repo_root())),
        "version": doc["version"],
        "entry_count": len(merged_list),
    }
