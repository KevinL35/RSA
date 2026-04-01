#!/usr/bin/env python3
"""TA-10：用快照 YAML 中的 entries 全量替换 Supabase 中该 vertical 的 overlay（回滚）。"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from taxonomy_backfill_lib import append_audit_line, load_overlay_document, repo_root_from_here
from taxonomy_supabase_toolkit import get_supabase_client, replace_vertical_overlay


def main() -> int:
    here = Path(__file__).resolve().parent
    root = repo_root_from_here(here)
    parser = argparse.ArgumentParser(description="TA-10 rollback taxonomy overlay in Supabase from snapshot YAML.")
    parser.add_argument("--vertical", required=True, choices=["general", "electronics"])
    parser.add_argument("--snapshot", type=Path, required=True, help="publish 时生成的快照 yaml（entries 将写入库）")
    parser.add_argument(
        "--audit-log",
        type=Path,
        default=root / "ml/reports/taxonomy_backfill_audit.jsonl",
    )
    args = parser.parse_args()

    if not args.snapshot.is_file():
        print(f"找不到快照: {args.snapshot}", file=sys.stderr)
        return 2

    try:
        sb = get_supabase_client()
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1

    doc = load_overlay_document(args.snapshot)
    entries = list(doc.get("entries") or [])
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    replace_vertical_overlay(sb, args.vertical, entries)
    append_audit_line(
        args.audit_log,
        {
            "action": "rollback",
            "vertical_id": args.vertical,
            "at_utc": ts,
            "snapshot_path": str(args.snapshot.resolve()),
            "entries_restored": len(entries),
            "target": "supabase://taxonomy_entries",
        },
    )
    print(f"已回滚 {args.vertical}：Supabase overlay 已替换为快照中 {len(entries)} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
