#!/usr/bin/env python3
"""从 Supabase `public.reviews` 导出 BERTopic 语料 CSV（与 TA-8 列约定对齐）。

需环境变量（与 apps/api 一致）：
  SUPABASE_URL       — Project URL，如 https://xxx.supabase.co
  SUPABASE_SERVICE_ROLE_KEY — service_role（仅本机/CI 使用，勿提交）

可选从仓库 `apps/api/.env` 自动加载（若变量尚未设置）。

模式
  默认：导出 reviews 表（可选 platform / product-id 过滤）。
  A 类（--only-without-dimension-hits）：仅导出指定洞察任务下「已有 review_analysis，
  但 review_dimension_analysis 无任何一行」的评论——用于词典未命中时的 BERTopic 补洞挖掘。

输出列：id, platform, product_id, text_en, created_at
  - text_en 由 raw_text 填入（当前 reviews 表无单独 analysis_input_en）
  - created_at 为 Unix 秒 UTC，供 run_bertopic_offline 时间窗过滤
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
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


def _rest_select_page(
    base: str,
    key: str,
    table: str,
    *,
    select: str,
    filters: list[tuple[str, str]],
    order: str,
    limit: int,
    offset: int,
) -> list[dict]:
    q: list[tuple[str, str]] = [
        ("select", select),
        ("order", order),
        ("limit", str(limit)),
        ("offset", str(offset)),
    ]
    q.extend(filters)
    url = f"{base.rstrip('/')}/rest/v1/{table}?{urllib.parse.urlencode(q)}"
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


def _fetch_page_reviews(
    base: str,
    key: str,
    *,
    filters: list[tuple[str, str]],
    limit: int,
    offset: int,
) -> list[dict]:
    return _rest_select_page(
        base,
        key,
        "reviews",
        select="id,platform,product_id,raw_text,created_at",
        filters=filters,
        order="created_at.desc",
        limit=limit,
        offset=offset,
    )


def _collect_review_analysis_without_dimension_hits(
    base: str,
    key: str,
    insight_task_id: str,
    page_size: int,
) -> set[str]:
    """返回「有 review_analysis 但无任意 review_dimension_analysis 行」的 review_id 集合。"""
    task_filter = ("insight_task_id", f"eq.{insight_task_id}")

    with_hits: set[str] = set()
    offset = 0
    while True:
        batch = _rest_select_page(
            base,
            key,
            "review_dimension_analysis",
            select="review_analysis_id",
            filters=[task_filter],
            order="review_analysis_id.asc",
            limit=page_size,
            offset=offset,
        )
        if not batch:
            break
        for row in batch:
            rid = row.get("review_analysis_id")
            if rid is not None:
                with_hits.add(str(rid))
        if len(batch) < page_size:
            break
        offset += page_size

    target_review_ids: set[str] = set()
    offset = 0
    while True:
        batch = _rest_select_page(
            base,
            key,
            "review_analysis",
            select="id,review_id",
            filters=[task_filter],
            order="id.asc",
            limit=page_size,
            offset=offset,
        )
        if not batch:
            break
        for row in batch:
            ra_id = str(row.get("id", "")).strip()
            rev_id = str(row.get("review_id", "")).strip()
            if not ra_id or not rev_id:
                continue
            if ra_id not in with_hits:
                target_review_ids.add(rev_id)
        if len(batch) < page_size:
            break
        offset += page_size

    return target_review_ids


def _fetch_reviews_by_ids(
    base: str,
    key: str,
    ids: list[str],
    *,
    platform: str | None,
    product_id: str | None,
    chunk_size: int,
) -> list[dict]:
    """按 id 分批拉取 reviews；可选 platform / product_id 再过滤。"""
    out: list[dict] = []
    for i in range(0, len(ids), chunk_size):
        chunk = ids[i : i + chunk_size]
        in_list = ",".join(chunk)
        filters: list[tuple[str, str]] = [("id", f"in.({in_list})")]
        if platform:
            filters.append(("platform", f"eq.{platform}"))
        if product_id:
            filters.append(("product_id", f"eq.{product_id}"))
        batch = _rest_select_page(
            base,
            key,
            "reviews",
            select="id,platform,product_id,raw_text,created_at",
            filters=filters,
            order="created_at.desc",
            limit=len(chunk),
            offset=0,
        )
        out.extend(batch)
    return out


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
    parser.add_argument("--limit", type=int, default=0, help="最多导出行数，0 表示不限制")
    parser.add_argument("--page-size", type=int, default=1000, help="Supabase 分页大小（≤1000 较稳）")
    parser.add_argument(
        "--insight-task-id",
        default=None,
        help="洞察任务 UUID；与 --only-without-dimension-hits 联用（A 类：已分析但无六维命中行）",
    )
    parser.add_argument(
        "--only-without-dimension-hits",
        action="store_true",
        help="仅导出 A 类：该任务下存在 review_analysis 且 review_dimension_analysis 为空",
    )
    args = parser.parse_args()

    if args.only_without_dimension_hits:
        tid = (args.insight_task_id or "").strip()
        if not tid:
            print("使用 --only-without-dimension-hits 时必须提供 --insight-task-id", file=sys.stderr)
            return 2
        if not _UUID_RE.match(tid):
            print(f"无效的 insight_task_id（应为 UUID）：{tid!r}", file=sys.stderr)
            return 2

    _load_api_dotenv()
    base = (os.environ.get("SUPABASE_URL") or "").strip().rstrip("/")
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not base or not key:
        print("缺少 SUPABASE_URL 或 SUPABASE_SERVICE_ROLE_KEY", file=sys.stderr)
        return 2

    page = max(1, min(args.page_size, 1000))
    total_cap = args.limit if args.limit and args.limit > 0 else None
    rows_out: list[tuple[str, str, str, str, int]] = []

    if args.only_without_dimension_hits:
        tid = args.insight_task_id.strip()
        review_ids = sorted(
            _collect_review_analysis_without_dimension_hits(base, key, tid, page),
        )
        print(
            f"[A 类] insight_task_id={tid}：无六维命中评论共 {len(review_ids)} 条（有 analysis 无 rda 行）",
            file=sys.stderr,
        )
        if not review_ids:
            rows_out = []
        else:
            # URL 长度限制：id=in.(...) 分批
            chunk_ids = 80
            all_rows = _fetch_reviews_by_ids(
                base,
                key,
                review_ids,
                platform=args.platform,
                product_id=args.product_id,
                chunk_size=chunk_ids,
            )
            by_id = {str(r["id"]): r for r in all_rows if r.get("id")}
            for rid in review_ids:
                r = by_id.get(rid)
                if not r:
                    continue
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
            rows_out.sort(key=lambda x: x[4], reverse=True)
            if total_cap is not None:
                rows_out = rows_out[:total_cap]
    else:
        filters: list[tuple[str, str]] = []
        if args.platform:
            filters.append(("platform", f"eq.{args.platform}"))
        if args.product_id:
            filters.append(("product_id", f"eq.{args.product_id}"))

        offset = 0
        while True:
            batch = _fetch_page_reviews(base, key, filters=filters, limit=page, offset=offset)
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
