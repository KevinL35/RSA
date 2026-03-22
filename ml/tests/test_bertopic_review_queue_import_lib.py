"""bertopic_review_queue_import_lib 纯逻辑单测（无网络）。"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import bertopic_review_queue_import_lib as lib  # noqa: E402


def test_build_payloads_skips_short_canonical() -> None:
    rows = [
        {"suggested_canonical": "x", "batch_id": "b1", "source_topic_id": "0"},
        {"suggested_canonical": "ok term", "batch_id": "b1", "source_topic_id": "1"},
    ]
    payloads, w = lib.build_queue_payloads_from_candidate_rows(rows)
    assert len(payloads) == 1
    assert payloads[0]["canonical"] == "ok term"
    assert payloads[0]["batch_id"] == "b1"
    assert payloads[0]["source_topic_id"] == "1"
    assert any("过短" in x for x in w)


def test_normalize_synonyms_dedupes() -> None:
    assert lib.normalize_synonyms("Battery", ["battery", "  Battery ", "life"]) == ["life"]


def test_invalid_dimension_cleared_with_warning() -> None:
    rows = [
        {
            "suggested_canonical": "foo bar",
            "batch_id": "b",
            "source_topic_id": "0",
            "dimension_6way": "not_a_dim",
        }
    ]
    payloads, w = lib.build_queue_payloads_from_candidate_rows(rows)
    assert payloads[0]["dimension_6way"] is None
    assert w
