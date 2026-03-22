#!/usr/bin/env python3
"""将 run_bertopic_offline.py 产出的 JSONL 写入 Supabase dictionary_review_queue。

每行 JSON 须符合 TA-9 候选结构（suggested_canonical、aliases、batch_id、source_topic_id、quality_score 等）。

环境变量（与 apps/api 一致）：
  SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
可选读取 apps/api/.env（若变量尚未设置）。

审核人在 Web「词典审核」中补/选六维、确认规范词与同义词后，走 POST /api/v1/dictionary/approve-entry 写入 overlay。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# TA-1 六维；仅当 JSONL 中 dimension_6way 合法时才写入队列，否则置空由审核人选
_VALID_DIMENSIONS = frozenset(
    {
        "pros",
        "cons",
        "return_reasons",
        "purchase_motivation",
        "user_expectation",
        "usage_scenario",
    },
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_api_dotenv() -> None:
    p = _repo_root() / "apps" / "api" / ".env"
    if not p.is_file():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, _, v = s.partition("=")
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def _http_json(
    method: str,
    url: str,
    *,
    key: str,
    body: object | None = None,
    extra_headers: dict[str, str] | None = None,
) -> tuple[int, str]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
    }
    if data is not None:
        headers["Content-Type"] = "application/json"
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        return e.code, raw


def _pending_exists(base: str, key: str, batch_id: str, source_topic_id: str) -> bool:
    q = urllib.parse.urlencode(
        {
            "batch_id": f"eq.{batch_id}",
            "source_topic_id": f"eq.{source_topic_id}",
            "status": "eq.pending",
            "select": "id",
            "limit": "1",
        }
    )
    url = f"{base.rstrip('/')}/rest/v1/dictionary_review_queue?{q}"
    code, raw = _http_json("GET", url, key=key)
    if code != 200:
        return False
    try:
        rows = json.loads(raw) if raw.strip() else []
    except json.JSONDecodeError:
        return False
    return isinstance(rows, list) and len(rows) > 0


def _normalize_synonyms(canonical: str, aliases: object) -> list[str]:
    c_low = canonical.strip().lower()
    out: list[str] = []
    seen: set[str] = set()
    if not isinstance(aliases, list):
        return out
    for a in aliases:
        s = str(a).strip()
        if not s or s.lower() == c_low:
            continue
        if s.lower() in seen:
            continue
        seen.add(s.lower())
        out.append(s)
    return out


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

    _load_api_dotenv()
    base = (os.environ.get("SUPABASE_URL") or "").strip().rstrip("/")
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not args.dry_run and (not base or not key):
        print("缺少 SUPABASE_URL 或 SUPABASE_SERVICE_ROLE_KEY（或加 --dry-run）", file=sys.stderr)
        return 2

    vertical_id = args.vertical_id.strip() or "general"
    payloads: list[dict] = []
    line_errors: list[str] = []

    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as e:
            line_errors.append(f"第 {i} 行 JSON 无效: {e}")
            continue

        suggested = str(row.get("suggested_canonical") or "").strip()
        if len(suggested) < 2:
            line_errors.append(f"第 {i} 行 suggested_canonical 过短，已跳过")
            continue

        batch_id = str(row.get("batch_id") or "").strip() or None
        source_topic_id = str(row.get("source_topic_id") or "").strip() or None
        if not batch_id or not source_topic_id:
            line_errors.append(f"第 {i} 行缺少 batch_id 或 source_topic_id，已跳过")
            continue

        aliases = _normalize_synonyms(suggested, row.get("aliases"))
        dim = row.get("dimension_6way")
        dim_s = dim.strip().lower() if isinstance(dim, str) and dim.strip() else None
        if dim_s is not None and dim_s not in _VALID_DIMENSIONS:
            line_errors.append(f"第 {i} 行 dimension_6way 无效 {dim_s!r}，已置空")
            dim_s = None

        qs = row.get("quality_score")
        quality: float | None
        if isinstance(qs, (int, float)):
            quality = float(qs)
        else:
            quality = None

        rec: dict = {
            "kind": args.kind,
            "canonical": suggested,
            "synonyms": aliases,
            "dictionary_vertical_id": vertical_id,
            "dimension_6way": dim_s,
            "batch_id": batch_id,
            "source_topic_id": source_topic_id,
            "status": "pending",
        }
        if quality is not None:
            rec["quality_score"] = quality
        payloads.append(rec)

    if line_errors:
        for msg in line_errors[:20]:
            print(msg, file=sys.stderr)
        if len(line_errors) > 20:
            print(f"... 另有 {len(line_errors) - 20} 条警告", file=sys.stderr)

    if args.dry_run:
        print(f"[dry-run] 可插入 {len(payloads)} 行（已解析 {path}）")
        return 0

    inserted = 0
    skipped = 0
    url = f"{base}/rest/v1/dictionary_review_queue"
    for p in payloads:
        if args.skip_existing and _pending_exists(base, key, p["batch_id"], p["source_topic_id"]):
            skipped += 1
            continue
        code, raw = _http_json(
            "POST",
            url,
            key=key,
            body=p,
            extra_headers={"Prefer": "return=minimal"},
        )
        if code not in (200, 201):
            print(f"插入失败 HTTP {code}: {raw[:500]}", file=sys.stderr)
            return 3
        inserted += 1

    print(f"已插入 {inserted} 行；跳过（已存在 pending）{skipped} 行。请到 Web「词典审核」处理。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
