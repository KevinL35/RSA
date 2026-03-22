#!/usr/bin/env python3
"""从 Supabase `public.reviews` 导出 BERTopic 语料 CSV（与 TA-8 列约定对齐）。

需环境变量（与 apps/api 一致）：
  SUPABASE_URL       — Project URL，如 https://xxx.supabase.co
  SUPABASE_SERVICE_ROLE_KEY — service_role（仅本机/CI 使用，勿提交）

可选从仓库 `apps/api/.env` 自动加载（若变量尚未设置）。

输出列：id, platform, product_id, text_en, created_at
  - text_en 由 raw_text 填入（当前 reviews 表无单独 analysis_input_en）
  - created_at 为 Unix 秒 UTC，供 run_bertopic_offline 时间窗过滤
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


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


def _parse_ts_iso(val: str) -> int:
    """PostgREST timestamptz ISO 字符串 -> Unix 秒 UTC。"""
    s = val.replace("Z", "+00:00")
    if s.endswith("+00:00") or "+" in s[10:] or s.count("-") > 2:
        dt = datetime.fromisoformat(s)
    else:
        dt = datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def _fetch_page(
    base: str,
    key: str,
    *,
    select: str,
    filters: list[tuple[str, str]],
    limit: int,
    offset: int,
) -> list[dict]:
    q: list[tuple[str, str]] = [
        ("select", select),
        ("order", "created_at.desc"),
        ("limit", str(limit)),
        ("offset", str(offset)),
    ]
    q.extend(filters)
    url = f"{base.rstrip('/')}/rest/v1/reviews?{urllib.parse.urlencode(q)}"
    req = urllib.request.Request(
        url,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Supabase HTTP {e.code}: {body}") from e
    data = json.loads(raw) if raw.strip() else []
    if not isinstance(data, list):
        raise RuntimeError("预期 JSON 数组")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Export Supabase reviews -> BERTopic corpus CSV.")
    parser.add_argument(
        "--out",
        type=Path,
        default=_repo_root() / "ml/data/bertopic_corpus_from_supabase.csv",
        help="输出 CSV 路径（默认 ml/data/bertopic_corpus_from_supabase.csv）",
    )
    parser.add_argument("--platform", default=None, help="仅导出该平台（PostgREST eq）")
    parser.add_argument("--product-id", default=None, help="仅导出该 ASIN/SKU 等 product_id")
    parser.add_argument("--limit", type=int, default=0, help="最多导出行数，0 表示不限制（分页直至取完）")
    parser.add_argument("--page-size", type=int, default=1000, help="每页条数（≤1000 较稳）")
    args = parser.parse_args()

    _load_api_dotenv()
    base = (os.environ.get("SUPABASE_URL") or "").strip().rstrip("/")
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not base or not key:
        print("缺少 SUPABASE_URL 或 SUPABASE_SERVICE_ROLE_KEY", file=sys.stderr)
        return 2

    filters: list[tuple[str, str]] = []
    if args.platform:
        filters.append(("platform", f"eq.{args.platform}"))
    if args.product_id:
        filters.append(("product_id", f"eq.{args.product_id}"))

    select = "id,platform,product_id,raw_text,created_at"
    page = max(1, min(args.page_size, 1000))
    offset = 0
    rows_out: list[tuple[str, str, str, str, int]] = []
    total_cap = args.limit if args.limit and args.limit > 0 else None

    while True:
        batch = _fetch_page(base, key, select=select, filters=filters, limit=page, offset=offset)
        if not batch:
            break
        for r in batch:
            rid = str(r.get("id", "")).strip()
            plat = str(r.get("platform", "")).strip()
            pid = str(r.get("product_id", "")).strip()
            text = str(r.get("raw_text") or "").strip()
            ca = r.get("created_at")
            if not text or not plat or not pid:
                continue
            if ca is None:
                ts = 0
            elif isinstance(ca, (int, float)):
                ts = int(ca)
            else:
                try:
                    ts = _parse_ts_iso(str(ca))
                except (ValueError, TypeError):
                    ts = 0
            rows_out.append((rid, plat, pid, text, ts))
            if total_cap is not None and len(rows_out) >= total_cap:
                break
        if total_cap is not None and len(rows_out) >= total_cap:
            break
        if len(batch) < page:
            break
        offset += page

    args.out.parent.mkdir(parents=True, exist_ok=True)

    with args.out.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "platform", "product_id", "text_en", "created_at"])
        for rid, plat, pid, text, ts in rows_out:
            w.writerow([rid, plat, pid, text, ts])

    print(f"已导出 {len(rows_out)} 行 -> {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
