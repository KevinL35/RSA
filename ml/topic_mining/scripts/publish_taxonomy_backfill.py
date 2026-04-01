#!/usr/bin/env python3
"""TA-10：将审核决策 JSONL 合并进指定垂直的 Supabase overlay，并写 YAML 快照与审计日志。"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from taxonomy_backfill_lib import (
    append_audit_line,
    group_approve_by_vertical,
    load_decisions_jsonl,
    merge_entries,
    repo_root_from_here,
    write_snapshot_document,
)
from taxonomy_supabase_toolkit import (
    export_overlay_document,
    fetch_overlay_rows,
    get_supabase_client,
    replace_vertical_overlay,
)

ALLOWED_VERTICALS = frozenset({"general", "electronics"})


def main() -> int:
    here = Path(__file__).resolve().parent
    root = repo_root_from_here(here)
    parser = argparse.ArgumentParser(description="TA-10 publish approved taxonomy backfill to Supabase.")
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
        help="发布前 overlay 快照目录（YAML，仅备份）",
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

    if args.dry_run:
        for vid in sorted(by_v):
            new_entries = by_v[vid]
            print(f"[dry-run] {vid}: 将合并 {len(new_entries)} 条 -> Supabase overlay")
        print(f"[dry-run] 统计: reject={n_reject}, hold={n_hold}")
        return 0

    try:
        sb = get_supabase_client()
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for vid in sorted(by_v):
        new_entries = by_v[vid]

        snap_path = None
        if not args.skip_snapshot:
            doc_before = export_overlay_document(sb, vid)
            snap_path = write_snapshot_document(doc_before, args.snapshots_dir, vertical_id=vid)

        existing = fetch_overlay_rows(sb, vid)
        prev_n = len(existing)
        merged = merge_entries(list(existing), new_entries)
        replace_vertical_overlay(sb, vid, merged)

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
                "snapshot_path": str(snap_path.resolve()) if snap_path else None,
                "target": "supabase://taxonomy_entries",
            },
        )
        print(f"已发布 {vid}: overlay 全量替换为 {len(merged)} 条（Supabase）")

    if decisions:
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
