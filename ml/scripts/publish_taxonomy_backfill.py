#!/usr/bin/env python3
"""TA-10：将审核决策 JSONL 合并进指定垂直的 overlay YAML，并写快照与审计日志。"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from taxonomy_backfill_lib import (
    append_audit_line,
    bump_patch_version,
    group_approve_by_vertical,
    load_decisions_jsonl,
    load_overlay_document,
    merge_entries,
    overlay_yaml_path,
    repo_root_from_here,
    snapshot_file,
    write_overlay_document,
)

ALLOWED_VERTICALS = frozenset({"general", "electronics"})


def main() -> int:
    here = Path(__file__).resolve().parent
    root = repo_root_from_here(here)
    parser = argparse.ArgumentParser(description="TA-10 publish approved taxonomy backfill.")
    parser.add_argument("--decisions", type=Path, required=True, help="审核决策 JSONL（每行一 JSON）")
    parser.add_argument(
        "--audit-log",
        type=Path,
        default=root / "ml/reports/taxonomy_backfill_audit.jsonl",
        help="审计追加路径（默认 ml/reports/，目录常已被 gitignore）",
    )
    parser.add_argument(
        "--snapshots-dir",
        type=Path,
        default=root / "ml/artifacts/taxonomy_snapshots",
        help="发布前 overlay 快照目录",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-snapshot", action="store_true")
    args = parser.parse_args()

    if not args.decisions.is_file():
        print(f"找不到决策文件: {args.decisions}", file=sys.stderr)
        return 2

    decisions = load_decisions_jsonl(args.decisions)
    by_v = group_approve_by_vertical(decisions)
    unknown = set(by_v) - ALLOWED_VERTICALS
    if unknown:
        print(f"不支持的 vertical_id: {unknown}，允许 {sorted(ALLOWED_VERTICALS)}", file=sys.stderr)
        return 2

    n_reject = sum(1 for r in decisions if r["decision"] == "reject")
    n_hold = sum(1 for r in decisions if r["decision"] == "hold")

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for vid in sorted(by_v):
        overlay_path = overlay_yaml_path(root, vid)
        new_entries = by_v[vid]
        if args.dry_run:
            print(f"[dry-run] {vid}: 将合并 {len(new_entries)} 条 -> {overlay_path}")
            continue

        snap_path = None
        if not args.skip_snapshot:
            snap_path = snapshot_file(overlay_path, args.snapshots_dir, vertical_id=vid)

        doc = load_overlay_document(overlay_path)
        prev_n = len(doc.get("entries") or [])
        merged = merge_entries(list(doc.get("entries") or []), new_entries)
        doc["entries"] = merged
        doc["version"] = bump_patch_version(str(doc.get("version") or "1.0.0"))
        write_overlay_document(overlay_path, doc)

        append_audit_line(
            args.audit_log,
            {
                "action": "publish",
                "vertical_id": vid,
                "at_utc": ts,
                "decisions_file": str(args.decisions.resolve()),
                "approved_merged": len(new_entries),
                "entries_before": prev_n,
                "entries_after": len(merged),
                "overlay_version": doc["version"],
                "snapshot_path": str(snap_path.resolve()) if snap_path else None,
            },
        )
        print(f"已发布 {vid}: +{len(new_entries)} 条，version={doc['version']}，overlay={overlay_path}")

    if args.dry_run:
        print(f"[dry-run] 统计: reject={n_reject}, hold={n_hold}")
    elif decisions:
        append_audit_line(
            args.audit_log,
            {
                "action": "publish_batch_summary",
                "at_utc": ts,
                "decisions_file": str(args.decisions.resolve()),
                "reject_count": n_reject,
                "hold_count": n_hold,
                "approve_verticals": sorted(by_v),
            },
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
