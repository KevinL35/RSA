"""TA-9：bertopic_offline_lib 纯逻辑单测（无需安装 bertopic）。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import bertopic_offline_lib as lib  # noqa: E402


def test_normalize_requires_text_column():
    df = pd.DataFrame({"platform": ["a"], "product_id": ["1"]})
    with pytest.raises(ValueError, match="text_en"):
        lib.normalize_corpus_columns(df)


def test_filter_by_time_window():
    # batch_end = 1700000000 + 86400, window 1 day -> [1700000000, 1700086400)
    batch_end = 1700086400
    df = pd.DataFrame(
        {
            "_text": ["a", "b", "c"],
            "created_at": [1700000000, 1700086300, 1700086400],
        }
    )
    out, ok = lib.filter_by_time_window(df, batch_end, 1)
    assert ok
    assert len(out) == 2


def test_iter_slices_respects_min_docs():
    rows = []
    for i in range(250):
        rows.append(
            {
                "platform": "amazon",
                "product_id": "P1",
                "_text": f"review text number {i} about quality and shipping",
                "created_at": 1700000000 + i * 3600,
            }
        )
    df = pd.DataFrame(rows)
    slices = list(lib.iter_slices(df, ["platform", "product_id"], 200))
    assert len(slices) == 1
    key, g = slices[0]
    assert key == ("amazon", "P1")
    assert len(g) == 250


def test_topic_quality_score_monotonic():
    q1 = lib.topic_quality_score(10, 0.05, 100)
    q2 = lib.topic_quality_score(80, 0.09, 100)
    assert q2 >= q1


def test_run_manifest_roundtrip(tmp_path):
    m = lib.RunManifest(
        batch_id="b1",
        batch_end_ts=1700000000,
        window_days=90,
        corpus_schema_version="ta8-v1",
    )
    m.slices.append({"platform": "x", "product_id": "y", "n_docs": 5})
    p = tmp_path / "run.json"
    m.write(p)
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["batch_id"] == "b1"
    assert data["window_days"] == 90


def test_candidate_record_schema():
    r = lib.candidate_record(
        batch_id="b",
        platform="amazon",
        product_id="asin",
        source_topic_id="3",
        suggested_canonical="battery life",
        aliases=["battery", "charge"],
        quality_score=77.5,
        quality_components={"topic_document_count": 40},
        evidence_snippets=["short doc a", "short doc b"],
    )
    assert r["dimension_6way"] is None
    assert r["suggested_canonical"] == "battery life"
