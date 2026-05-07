#!/usr/bin/env python3
"""
独立调试 Pangolin 评论抓取（与 Platform API 共用 app 内逻辑与 .env）。

在项目根目录执行：

  PYTHONPATH=backend/platform-api .venv/bin/python scripts/fetch_reviews_pangolin.py
  PYTHONPATH=backend/platform-api .venv/bin/python scripts/fetch_reviews_pangolin.py B0FHQ9LPF2

可选（在导入前写入环境变量，用于试更小 pageCount）：

  PANGOLIN_PAGE_COUNT_MAX=2 PYTHONPATH=backend/platform-api .venv/bin/python scripts/fetch_reviews_pangolin.py

依赖：已安装 platform-api 的依赖（与 dev 相同 .venv 即可）。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_PLATFORM_API = _ROOT / "backend" / "platform-api"


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


if not _PLATFORM_API.is_dir():
    _log(f"错误：未找到 platform-api 目录：{_PLATFORM_API}")
    sys.exit(2)
sys.path.insert(0, str(_PLATFORM_API))


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Pangolin 评论抓取调试脚本（amazon）")
    p.add_argument(
        "asin",
        nargs="?",
        default="B0FHQ9LPF2",
        help="商品 ASIN（默认 B0FHQ9LPF2）",
    )
    p.add_argument(
        "--page-count",
        type=int,
        default=None,
        metavar="N",
        help="覆盖 PANGOLIN_PAGE_COUNT（仅本次进程）",
    )
    p.add_argument(
        "--page-count-max",
        type=int,
        default=None,
        metavar="N",
        help="覆盖 PANGOLIN_PAGE_COUNT_MAX（仅本次进程）",
    )
    p.add_argument(
        "--quick",
        action="store_true",
        help="单页探测：等价于 --page-count 1 --page-count-max 1（仍 504 多为上游问题）",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="将规范化后的评论列表以 JSON 打印到 stdout",
    )
    p.add_argument(
        "--limit-json",
        type=int,
        default=5,
        metavar="N",
        help="与 --json 联用时最多输出前 N 条（默认 5，0 表示全部）",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    asin = (args.asin or "").strip()
    if not asin:
        _log("错误：ASIN 为空")
        return 2
    if args.quick:
        os.environ["PANGOLIN_PAGE_COUNT"] = "1"
        os.environ["PANGOLIN_PAGE_COUNT_MAX"] = "1"
    else:
        if args.page_count is not None:
            os.environ["PANGOLIN_PAGE_COUNT"] = str(max(1, int(args.page_count)))
        if args.page_count_max is not None:
            os.environ["PANGOLIN_PAGE_COUNT_MAX"] = str(max(1, int(args.page_count_max)))

    from app.core.config import get_settings
    from app.integrations.review_provider import ReviewProviderError, fetch_reviews_normalized

    settings = get_settings()
    mode = (settings.review_provider_mode or "").strip().lower()
    _log(f"REVIEW_PROVIDER_MODE={mode!r}")
    if mode != "pangolin":
        _log("提示：当前不是 pangolin 模式，将按 .env 中的模式调用 fetch_reviews_normalized。")
    if not (settings.pangolin_token or "").strip() and mode == "pangolin":
        _log("错误：PANGOLIN_TOKEN 未配置（检查 backend/platform-api/.env）")
        return 2

    _log(
        f"PANGOLIN_PAGE_COUNT={settings.pangolin_page_count} "
        f"PANGOLIN_PAGE_COUNT_MAX={settings.pangolin_page_count_max} "
        f"timeout_s={settings.pangolin_timeout_seconds}"
    )
    _log(
        "说明：若日志出现「pangolin HTTP 504 … pageCount 10 -> 5」，表示对方网关超时，"
        "已在自动减半页数并重试；单次请求可能需数十秒～数分钟，请耐心等待。"
        "想先试最小请求可加参数：--quick"
    )
    _log(f"开始抓取 amazon / {asin} …")

    try:
        rows = fetch_reviews_normalized("amazon", asin, settings=settings)
    except ReviewProviderError as e:
        _log(f"失败 {e.code}: {e.message}")
        return 1

    n = len(rows)
    _log(f"成功：共 {n} 条可入库评论")
    if n == 0:
        _log("（供应商返回成功但解析后 0 条，可能是无评论或字段结构变化）")
        return 0

    if args.json:
        out = rows
        lim = int(args.limit_json)
        if lim > 0:
            out = rows[:lim]
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        for i, r in enumerate(rows[:5], 1):
            rid = r.get("external_review_id") or "?"
            text = (r.get("raw_text") or "")[:120].replace("\n", " ")
            _log(f"  [{i}] {rid}  {text!r}...")
        if n > 5:
            _log(f"  ... 另有 {n - 5} 条（加 --json 查看）")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
