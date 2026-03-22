"""TA-10：taxonomy_backfill_lib 单测（需 PyYAML；pandas 非必须）。"""

from __future__ import annotations

import json
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_taxonomy_backfill_lib():
    path = Path(__file__).resolve().parent.parent / "scripts" / "taxonomy_backfill_lib.py"
    spec = spec_from_file_location("taxonomy_backfill_lib", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载 {path}")
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


t = _load_taxonomy_backfill_lib()


def test_bump_patch_version():
    assert t.bump_patch_version("1.0.0") == "1.0.1"
    assert t.bump_patch_version("2.3.9") == "2.3.10"


def test_merge_entries_overlay_wins():
    base = [{"dimension_6way": "cons", "canonical": "x", "priority": 1}]
    over = [{"dimension_6way": "cons", "canonical": "x", "priority": 99}]
    m = t.merge_entries(base, over)
    assert len(m) == 1
    assert m[0]["priority"] == 99


def test_load_decisions_jsonl(tmp_path):
    p = tmp_path / "d.jsonl"
    p.write_text(
        json.dumps(
            {
                "decision": "approve",
                "vertical_id": "general",
                "batch_id": "b1",
                "source_topic_id": "1",
                "dimension_6way": "pros",
                "canonical": "great value",
                "aliases": ["good deal"],
                "reviewer": "alice",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    rows = t.load_decisions_jsonl(p)
    assert len(rows) == 1
    by_v = t.group_approve_by_vertical(rows)
    assert "general" in by_v
    assert by_v["general"][0]["canonical"] == "great value"
    assert by_v["general"][0]["entry_source"] == "bertopic"


def test_parse_reject_without_canonical(tmp_path):
    p = tmp_path / "d.jsonl"
    p.write_text(
        json.dumps(
            {
                "decision": "reject",
                "vertical_id": "electronics",
                "reviewer": "bob",
                "notes": "bad",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    rows = t.load_decisions_jsonl(p)
    assert rows[0]["decision"] == "reject"


def test_overlay_roundtrip(tmp_path):
    doc = {
        "version": "1.0.0",
        "taxonomy_id": "t-test",
        "description": "x",
        "entries": [{"dimension_6way": "cons", "canonical": "a", "aliases": [], "weight": 1.0, "priority": 5}],
    }
    path = tmp_path / "o.yaml"
    t.write_overlay_document(path, doc)
    loaded = t.load_overlay_document(path)
    assert loaded["entries"][0]["canonical"] == "a"
