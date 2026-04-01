"""TA-10：词典回灌（决策校验、overlay 读写、快照与审计行）。"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

DIMENSION_KEYS = frozenset(
    {
        "pros",
        "cons",
        "return_reasons",
        "purchase_motivation",
        "user_expectation",
        "usage_scenario",
    }
)

VALID_DECISIONS = frozenset({"approve", "reject", "hold"})


def repo_root_from_here(here: Path) -> Path:
    """ml/topic_mining/scripts/xxx.py -> 仓库根。"""
    return here.resolve().parents[2]


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
    """仅升补丁位，如 1.0.0 -> 1.0.1；解析失败则在末尾加 .1。"""
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)(.*)$", v.strip())
    if not m:
        return (v.strip() + ".1") if v.strip() else "1.0.1"
    major, minor, patch, rest = m.group(1), m.group(2), m.group(3), m.group(4) or ""
    return f"{major}.{minor}.{int(patch) + 1}{rest}"


def approved_entry_from_decision(row: dict[str, Any]) -> dict[str, Any]:
    """将 approve 决策转为 YAML 词条（含溯源字段，归因引擎忽略未知键）。"""
    dim = str(row.get("dimension_6way", "")).strip().lower()
    if dim not in DIMENSION_KEYS:
        raise ValueError(f"无效 dimension_6way: {row.get('dimension_6way')!r}")
    canonical = str(row.get("canonical", "")).strip()
    if len(canonical) < 2:
        raise ValueError("canonical 至少 2 字符")
    aliases = row.get("aliases") or []
    if isinstance(aliases, str):
        aliases = [aliases]
    if not isinstance(aliases, list):
        aliases = []
    aliases = [str(a).strip() for a in aliases if str(a).strip()]
    priority = int(row.get("priority", 50))
    weight = float(row.get("weight", 1.0))
    ent: dict[str, Any] = {
        "dimension_6way": dim,
        "canonical": canonical,
        "aliases": aliases,
        "weight": weight,
        "priority": priority,
        "entry_source": "bertopic",
        "provenance": {
            "batch_id": row.get("batch_id"),
            "source_topic_id": row.get("source_topic_id"),
            "reviewer": row.get("reviewer"),
            "reviewed_at": row.get("reviewed_at"),
        },
    }
    return ent


def parse_decision_row(row: dict[str, Any], line_no: int) -> dict[str, Any]:
    d = str(row.get("decision", "")).strip().lower()
    if d not in VALID_DECISIONS:
        raise ValueError(f"行 {line_no}: 无效 decision {row.get('decision')!r}")
    vid = str(row.get("vertical_id", "")).strip()
    if not vid:
        raise ValueError(f"行 {line_no}: 缺少 vertical_id")
    reviewer = str(row.get("reviewer", "")).strip()
    if not reviewer:
        raise ValueError(f"行 {line_no}: 缺少 reviewer")
    if d == "approve":
        approved_entry_from_decision({**row, "reviewer": reviewer})  # validate
    return {**row, "decision": d, "vertical_id": vid, "reviewer": reviewer}


def load_decisions_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    text = path.read_text(encoding="utf-8")
    for i, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"行 {i}: 须为 JSON object")
        out.append(parse_decision_row(row, i))
    return out


def group_approve_by_vertical(decisions: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_v: dict[str, list[dict[str, Any]]] = {}
    for row in decisions:
        if row.get("decision") != "approve":
            continue
        vid = row["vertical_id"]
        by_v.setdefault(vid, []).append(approved_entry_from_decision(row))
    return by_v


def default_snapshots_dir(root: Path) -> Path:
    return root / "ml" / "artifacts" / "taxonomy_snapshots"


def write_snapshot_document(
    doc: dict[str, Any],
    snapshots_dir: Path,
    *,
    vertical_id: str,
) -> Path:
    """将词典文档写入 ml/artifacts/taxonomy_snapshots（发布前备份）。"""
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = snapshots_dir / f"{vertical_id}_overlay_{ts}.yaml"
    write_overlay_document(dest, doc)
    return dest


def append_audit_line(
    audit_path: Path,
    record: dict[str, Any],
) -> None:
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
