#!/usr/bin/env python3
"""
给定 Amazon 商品 ASIN 列表，通过 Pangolinfo Amazon Review API 抓取评论。

文档：https://docs.pangolinfo.com/cn-api-reference/amazonReviewAPI/amazonReviewAPI
请求体与 apps/platform-api/app/integrations/review_provider/pangolin.py 一致。

认证：环境变量 PANGOLIN_TOKEN（Bearer，见控制台 POST /api/v1/auth 返回的 data）。

依赖：pip install httpx openpyxl

示例：
  export PANGOLIN_TOKEN='你的token'

  # 导出 Excel 到桌面（默认每个 ASIN 拉满 pageCount=100 页，尽量多抓；积点见官方文档）
  python scripts/pangolinfo_asin_reviews.py --asin-file scripts/pangolinfo_sample_asins.txt --desktop

  # 限制页数（例如只拉 10 页）
  python scripts/pangolinfo_asin_reviews.py --asin-file asins.txt --review-pages 10 -o ~/Desktop/评论.xlsx

  # JSONL
  python scripts/pangolinfo_asin_reviews.py --asin-file asins.txt -o reviews.jsonl

积点：评论约 5 积点/页（以官方为准）。请合规使用。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from typing import Any

try:
    import httpx
except ImportError:
    print("请先安装：pip install httpx", file=sys.stderr)
    raise SystemExit(1)

DEFAULT_BASE = "https://scrapeapi.pangolinfo.com"
DEFAULT_AMAZON = "https://www.amazon.com"
DEFAULT_ZIP = "10041"
DEFAULT_REVIEW_PARSER = "amzReviewV2"
# 与 apps/platform-api pangolin 一致：单次请求 pageCount 上限，尽量多抓
DEFAULT_REVIEW_PAGES = 100
MAX_REVIEW_PAGES = 100


def _default_page_count() -> int:
    v = os.environ.get("PANGOLIN_PAGE_COUNT", "").strip()
    if not v:
        return DEFAULT_REVIEW_PAGES
    try:
        return max(1, int(v))
    except ValueError:
        return DEFAULT_REVIEW_PAGES


def _default_max_pages() -> int:
    v = os.environ.get("PANGOLIN_PAGE_COUNT_MAX", "").strip()
    if not v:
        return MAX_REVIEW_PAGES
    try:
        return max(1, min(int(v), MAX_REVIEW_PAGES))
    except ValueError:
        return MAX_REVIEW_PAGES


ASIN_RE = re.compile(r"^B[A-Z0-9]{9}$")


def _extract_result_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    data = payload.get("data")
    if not isinstance(data, dict):
        return rows
    json_arr = data.get("json")
    if not isinstance(json_arr, list):
        return rows
    for block in json_arr:
        entry: Any = block
        if isinstance(block, str):
            try:
                entry = json.loads(block)
            except (json.JSONDecodeError, TypeError):
                continue
        if not isinstance(entry, dict):
            continue
        inner = entry.get("data")
        if not isinstance(inner, dict):
            continue
        results = inner.get("results")
        if isinstance(results, list):
            for r in results:
                if isinstance(r, dict):
                    rows.append(r)
    return rows


def _map_review(r: dict[str, Any]) -> dict[str, Any] | None:
    text = r.get("content") or r.get("body") or r.get("text")
    if text is None or not str(text).strip():
        return None
    out: dict[str, Any] = {
        "content": str(text).strip(),
        "review_id": r.get("reviewId") or r.get("review_id") or r.get("id"),
        "title": r.get("title"),
        "star": r.get("star"),
        "date": r.get("date"),
        "author": r.get("author"),
    }
    return {k: v for k, v in out.items() if v is not None}


def _post_scrape(
    client: httpx.Client,
    base: str,
    token: str,
    body: dict[str, Any],
    *,
    timeout_sec: float = 120.0,
) -> dict[str, Any]:
    url = f"{base.rstrip('/')}/api/v1/scrape"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    resp = client.post(
        url,
        json=body,
        headers=headers,
        timeout=httpx.Timeout(max(120.0, timeout_sec), connect=30.0),
    )
    resp.raise_for_status()
    payload = resp.json()
    if not isinstance(payload, dict):
        raise ValueError("响应不是 JSON 对象")
    if payload.get("code") != 0:
        raise RuntimeError(
            f"Pangolinfo 业务错误 code={payload.get('code')}: {payload.get('message')}"
        )
    return payload


def fetch_reviews_for_asin(
    client: httpx.Client,
    *,
    base: str,
    token: str,
    amazon_base: str,
    asin: str,
    page_count: int,
    filter_by_star: str,
    sort_by: str,
) -> list[dict[str, Any]]:
    body: dict[str, Any] = {
        "url": amazon_base.rstrip("/"),
        "bizContext": {
            "bizKey": "review",
            "pageCount": page_count,
            "asin": asin.strip(),
            "filterByStar": filter_by_star,
            "sortBy": sort_by,
        },
        "format": "json",
        "parserName": DEFAULT_REVIEW_PARSER,
    }
    # 页数多时 Pangolinfo 耗时会变长
    timeout_sec = min(600.0, 90.0 + float(page_count) * 5.0)
    payload = _post_scrape(client, base, token, body, timeout_sec=timeout_sec)
    rows = _extract_result_rows(payload)
    out: list[dict[str, Any]] = []
    for r in rows:
        m = _map_review(r)
        if m:
            out.append(m)
    return out


def _dedupe_review_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """同一 ASIN 下按 review_id 去重；无 id 时按正文去重。"""
    seen: set[tuple[str, str]] = set()
    out: list[dict[str, Any]] = []
    for r in rows:
        asin = str(r.get("asin", "") or "")
        rid = str(r.get("review_id", "") or "").strip()
        content = str(r.get("content", "") or "").strip()
        key = (asin, rid if rid else content[:200])
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def parse_asin_list(arg_asins: str | None, asin_file: str | None) -> list[str]:
    raw: list[str] = []
    if arg_asins:
        raw.extend(a.strip() for a in arg_asins.split(",") if a.strip())
    if asin_file:
        path = os.path.expanduser(asin_file)
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                raw.append(line.split()[0].strip())

    seen: set[str] = set()
    out: list[str] = []
    for a in raw:
        u = a.strip().upper()
        if not ASIN_RE.match(u):
            print(f"跳过无效 ASIN: {a!r}", file=sys.stderr)
            continue
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _desktop_dir() -> str:
    home = os.path.expanduser("~")
    # macOS 中文版系统常见「桌面」
    for name in ("Desktop", "桌面"):
        d = os.path.join(home, name)
        if os.path.isdir(d):
            return d
    return home


def write_reviews_xlsx(path: str, rows: list[dict[str, Any]]) -> None:
    try:
        from openpyxl import Workbook
    except ImportError:
        print("导出 Excel 需要：pip install openpyxl", file=sys.stderr)
        raise SystemExit(3)

    wb = Workbook()
    ws = wb.active
    ws.title = "reviews"
    ws.append(["ASIN", "评论"])
    for r in rows:
        ws.append(
            [
                str(r.get("asin", "") or ""),
                str(r.get("content", "") or ""),
            ]
        )
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    wb.save(path)


def main() -> None:
    p = argparse.ArgumentParser(description="按 ASIN 抓取 Amazon 评论（Pangolinfo）")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument(
        "--asins",
        help="逗号分隔的 ASIN，例如：B076CLQDR4,B0DYTF8L2W",
    )
    g.add_argument(
        "--asin-file",
        metavar="PATH",
        help="每行一个 ASIN；可含空行与 # 注释",
    )
    p.add_argument(
        "--review-pages",
        type=int,
        default=_default_page_count(),
        help=f"每个 ASIN 的评论页数 pageCount，默认 {DEFAULT_REVIEW_PAGES}（尽量多抓）；可用环境变量 PANGOLIN_PAGE_COUNT 覆盖",
    )
    p.add_argument(
        "--max-review-pages",
        type=int,
        default=_default_max_pages(),
        help=f"pageCount 上限，默认 {MAX_REVIEW_PAGES}；可用 PANGOLIN_PAGE_COUNT_MAX",
    )
    p.add_argument(
        "--desktop",
        action="store_true",
        help="将 Excel 写到本机「桌面」目录，文件名带时间戳",
    )
    p.add_argument(
        "-o",
        "--output",
        default="",
        help="输出路径：.xlsx 为 Excel，否则为 JSONL；与 --desktop 二选一或 -o 优先",
    )
    p.add_argument("--base-url", default=os.environ.get("PANGOLIN_BASE_URL", DEFAULT_BASE))
    p.add_argument("--amazon-url", default=os.environ.get("PANGOLIN_AMAZON_URL", DEFAULT_AMAZON))
    p.add_argument("--filter-by-star", default="all_stars")
    p.add_argument("--sort-by", default="recent")
    p.add_argument("--sleep", type=float, default=1.0, help="ASIN 之间的请求间隔（秒）")
    args = p.parse_args()

    token = (os.environ.get("PANGOLIN_TOKEN") or "").strip()
    if not token:
        print("请设置环境变量 PANGOLIN_TOKEN", file=sys.stderr)
        raise SystemExit(2)

    asins = parse_asin_list(args.asins, args.asin_file)
    if not asins:
        print("没有有效的 ASIN", file=sys.stderr)
        raise SystemExit(2)

    cap = max(1, min(int(args.max_review_pages), MAX_REVIEW_PAGES))
    page_count = max(1, min(int(args.review_pages), cap))
    if page_count != int(args.review_pages):
        print(f"pageCount 已限制为 {page_count}（上限 {cap}）", file=sys.stderr)

    want_xlsx = bool(args.desktop) or (args.output.lower().endswith(".xlsx") if args.output else False)
    if args.desktop and args.output:
        print("已指定 -o 时将忽略 --desktop，使用 -o 路径", file=sys.stderr)

    out_path = ""
    if args.output:
        out_path = os.path.expanduser(args.output)
    elif args.desktop:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = os.path.join(_desktop_dir(), f"pangolinfo_amazon_reviews_{ts}.xlsx")
        want_xlsx = True

    all_rows: list[dict[str, Any]] = []

    with httpx.Client() as client:
        for asin in asins:
            print(f"# ASIN {asin} …", file=sys.stderr)
            time.sleep(max(0.0, args.sleep))
            reviews = fetch_reviews_for_asin(
                client,
                base=args.base_url,
                token=token,
                amazon_base=args.amazon_url,
                asin=asin,
                page_count=page_count,
                filter_by_star=args.filter_by_star,
                sort_by=args.sort_by,
            )
            for rev in reviews:
                all_rows.append({"asin": asin, **rev})
            print(f"  共 {len(reviews)} 条", file=sys.stderr)

    all_rows = _dedupe_review_rows(all_rows)
    print(f"# 去重后合计 {len(all_rows)} 条", file=sys.stderr)

    if want_xlsx:
        if not out_path:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_path = os.path.join(_desktop_dir(), f"pangolinfo_amazon_reviews_{ts}.xlsx")
        write_reviews_xlsx(out_path, all_rows)
        print(f"已写入 Excel：{out_path}（共 {len(all_rows)} 行）", file=sys.stderr)
        return

    if args.output:
        with open(out_path, "w", encoding="utf-8") as out_f:
            for row in all_rows:
                out_f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"已写入 JSONL：{out_path}（共 {len(all_rows)} 行）", file=sys.stderr)
        return

    for row in all_rows:
        print(json.dumps(row, ensure_ascii=False))


if __name__ == "__main__":
    main()
