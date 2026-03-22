#!/usr/bin/env python3
"""将 run_bertopic_offline.py 产出的 JSONL 写入 Supabase dictionary_review_queue。

每行 JSON 须符合 TA-9 候选结构（suggested_canonical、aliases、batch_id、source_topic_id、quality_score 等）。

环境变量（与 apps/platform-api 一致）：
  SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
可选读取 apps/platform-api/.env（若变量尚未设置）。

审核人在 Web「词典审核」中补/选六维、确认规范词与同义词后，走 POST /api/v1/dictionary/approve-entry 写入 overlay。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import bertopic_review_queue_import_lib as rq


def main() -> int:
    parser = argparse.ArgumentParser(description="Import BERTopic JSONL → dictionary_review_queue.")
    parser.add_argument(
        "--jsonl",
        type=Path,
        required=True,
        help="bertopic_candidates_{batch_id}.jsonl 路径",
    )
    parser.add_argument(
        "--vertical-id",
        default="general",
        help="默认 dictionary_vertical_id（审核通过时可改选多个类目）",
    )
    parser.add_argument(
        "--kind",
        choices=("new_discovery", "existing"),
        default="new_discovery",
        help="队列 kind；BERTopic 默认可用 new_discovery",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只解析并打印将插入的行数，不写库",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="若同一 batch_id+source_topic_id 已有 pending 行则跳过",
    )
    args = parser.parse_args()

    path = args.jsonl
    if not path.is_file():
        print(f"文件不存在: {path}", file=sys.stderr)
        return 2

    rq.load_platform_api_dotenv()
    base = (os.environ.get("SUPABASE_URL") or "").strip().rstrip("/")
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not args.dry_run and (not base or not key):
        print("缺少 SUPABASE_URL 或 SUPABASE_SERVICE_ROLE_KEY（或加 --dry-run）", file=sys.stderr)
        return 2

    rows: list[dict] = []
    line_errors: list[str] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            line_errors.append(f"第 {i} 行 JSON 无效: {e}")

    payloads, warnings = rq.build_queue_payloads_from_candidate_rows(
        rows,
        vertical_id=args.vertical_id,
        kind=args.kind,
    )
    all_notes = line_errors + warnings
    for msg in all_notes[:20]:
        print(msg, file=sys.stderr)
    if len(all_notes) > 20:
        print(f"... 另有 {len(all_notes) - 20} 条提示", file=sys.stderr)

    if args.dry_run:
        print(f"[dry-run] 可插入 {len(payloads)} 行（已解析 {path}）")
        return 0

    inserted, skipped, err = rq.import_payloads_to_dictionary_review_queue(
        payloads,
        skip_existing=args.skip_existing,
        supabase_url=base,
        service_role_key=key,
    )
    if err:
        print(f"插入失败 {err}", file=sys.stderr)
        return 3

    print(f"已插入 {inserted} 行；跳过（已存在 pending）{skipped} 行。请到 Web「词典审核」处理。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
