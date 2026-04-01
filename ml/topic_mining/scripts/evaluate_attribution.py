#!/usr/bin/env python3
"""
TA-7：对抽检 CSV 运行归因引擎，输出可复现 JSON 报告（可追溯率、确定性、可选金标维度）。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from attribution_engine import (
    attribute_review,
    build_patterns,
    load_taxonomy_yaml,
)


def _sha256(obj: object) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _parse_expected_dims(cell: str | None) -> set[str] | None:
    if cell is None:
        return None
    s = str(cell).strip()
    if s == "":
        return set()
    parts = {p.strip() for p in s.replace("|", ";").split(";") if p.strip()}
    return parts


def _is_nan_like(v: str) -> bool:
    t = str(v).strip().lower()
    return t in ("", "nan", "none")


def main() -> None:
    parser = argparse.ArgumentParser(description="TA-7 attribution batch eval → JSON report.")
    parser.add_argument("--dictionary", required=True, help="Path to taxonomy_dictionary_seed YAML.")
    parser.add_argument("--input", required=True, help="CSV with id, raw_text, analysis_input_en.")
    parser.add_argument(
        "--report",
        default="ml/reports/attribution_eval_v1.json",
        help="Output JSON path.",
    )
    parser.add_argument("--limit", type=int, default=0, help="Max rows (0 = all).")
    args = parser.parse_args()

    dict_path = Path(args.dictionary)
    in_path = Path(args.input)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    data = load_taxonomy_yaml(dict_path)
    patterns = build_patterns(data)

    with in_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    required = {"id", "raw_text", "analysis_input_en"}
    if not rows:
        raise SystemExit("Empty CSV")
    miss = required - set(rows[0].keys())
    if miss:
        raise SystemExit(f"Missing columns: {miss}")

    if args.limit and args.limit > 0:
        rows = rows[: args.limit]

    per_row: list[dict] = []
    trace_hits = 0
    trace_total = 0
    gold_rows = 0
    gold_dim_match = 0

    run_a: list[dict] = []
    run_b: list[dict] = []

    for row in rows:
        rid = str(row["id"])
        raw = str(row.get("raw_text") or "")
        ain = str(row.get("analysis_input_en") or "")
        dims_a, meta_a = attribute_review(rid, raw, ain, patterns)
        dims_b, meta_b = attribute_review(rid, raw, ain, patterns)
        run_a.append({"review_id": rid, "dimensions": dims_a})
        run_b.append({"review_id": rid, "dimensions": dims_b})

        if dims_a:
            trace_total += 1
            if meta_a.get("evidence_mapped_to_raw_text"):
                trace_hits += 1

        exp_cell = row.get("expected_dimensions")
        if "expected_dimensions" in row.keys():
            if exp_cell is None or (isinstance(exp_cell, str) and _is_nan_like(exp_cell)):
                exp = None
            else:
                exp = _parse_expected_dims(str(exp_cell))
            if exp is not None:
                gold_rows += 1
                pred = {d["dimension"] for d in dims_a}
                if pred == exp:
                    gold_dim_match += 1

        per_row.append(
            {
                "review_id": rid,
                "dimensions": dims_a,
                "evidence_mapped_to_raw_text": meta_a.get("evidence_mapped_to_raw_text"),
                "match_count": meta_a.get("match_count", 0),
            }
        )

    det_a = _sha256(run_a)
    det_b = _sha256(run_b)
    deterministic = det_a == det_b

    report = {
        "taxonomy_version": data.get("version"),
        "taxonomy_id": data.get("taxonomy_id"),
        "dictionary_path": str(dict_path.resolve()),
        "input_path": str(in_path.resolve()),
        "row_count": len(rows),
        "reviews_with_dimension_hits": trace_total,
        "evidence_traceable_to_raw_text_rate": (trace_hits / trace_total) if trace_total else None,
        "deterministic_repeat_runs": deterministic,
        "determinism_digest": det_a,
        "gold_dimension_rows": gold_rows,
        "gold_dimension_set_match_count": gold_dim_match,
        "gold_dimension_set_accuracy": (gold_dim_match / gold_rows) if gold_rows else None,
        "per_row": per_row,
    }

    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
