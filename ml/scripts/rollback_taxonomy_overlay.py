#!/usr/bin/env python3
"""TA-10：用快照 YAML 覆盖当前垂直 overlay（回滚）。"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from taxonomy_backfill_lib import append_audit_line, load_overlay_document, overlay_yaml_path, repo_root_from_here, write_overlay_document


def main() -> int:
    here = Path(__file__).resolve().parent
    root = repo_root_from_here(here)
    parser = argparse.ArgumentParser(description="TA-10 rollback taxonomy overlay from snapshot.")
    parser.add_argument("--vertical", required=True, choices=["general", "electronics"])
    parser.add_argument("--snapshot", type=Path, required=True, help="publish 时生成的快照 yaml")
    parser.add_argument(
        "--audit-log",
        type=Path,
        default=root / "ml/reports/taxonomy_backfill_audit.jsonl",
    )
    args = parser.parse_args()

    if not args.snapshot.is_file():
        print(f"找不到快照: {args.snapshot}", file=sys.stderr)
        return 2

    overlay_path = overlay_yaml_path(root, args.vertical)
    doc = load_overlay_document(args.snapshot)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    write_overlay_document(overlay_path, doc)
    append_audit_line(
        args.audit_log,
        {
            "action": "rollback",
            "vertical_id": args.vertical,
            "at_utc": ts,
            "snapshot_path": str(args.snapshot.resolve()),
            "overlay_path": str(overlay_path.resolve()),
            "entries_restored": len(doc.get("entries") or []),
        },
    )
    print(f"已回滚 {args.vertical} -> {overlay_path}（自快照 {args.snapshot}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
