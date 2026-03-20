#!/usr/bin/env python3
"""
将 Ni et al. Amazon Review Data (2018) 的「按行 JSON」(JSONL) 转为情感微调契约 CSV。

适用：如 Electronics_5.json / *.json.gz（每行一条 review，字段见官网说明）。
星级 overall → label_sentiment：1–2→0，3→1，4–5→2（与 Fine Food 导入一致）。

默认流式读写，适合 GB 级文件。
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import sys
from pathlib import Path


def open_maybe_gzip(path: Path):
    if path.suffix.lower() == ".gz" or str(path).endswith(".json.gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace", newline="")
    return path.open("r", encoding="utf-8", errors="replace", newline="")


def make_review_id(obj: dict) -> str:
    """稳定主键：reviewerID + asin + unixReviewTime（数据集中通常唯一）。"""
    rid = str(obj.get("reviewerID", "")).strip()
    asin = str(obj.get("asin", "")).strip()
    ts = int(obj.get("unixReviewTime") or 0)
    return f"{rid}_{asin}_{ts}"


def overall_to_label(overall) -> int | None:
    if overall is None:
        return None
    try:
        s = int(round(float(overall)))
    except (TypeError, ValueError):
        return None
    if s <= 2:
        return 0
    if s == 3:
        return 1
    if s <= 5:
        return 2
    return None


def build_body(obj: dict, prepend_summary: bool) -> str:
    text = (obj.get("reviewText") or "").strip()
    if not text:
        return ""
    if not prepend_summary:
        return text
    summ = (obj.get("summary") or "").strip()
    if not summ:
        return text
    return f"{summ}. {text}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Amazon 2018 JSONL reviews -> reviews.csv")
    parser.add_argument(
        "--input",
        default="finetune/data/raw/Electronics_5.json",
        help="输入 JSONL（或 .json.gz）路径",
    )
    parser.add_argument(
        "--output",
        default="finetune/data/raw/reviews.csv",
        help="输出 CSV（与 data_contract raw_input 一致）",
    )
    parser.add_argument(
        "--platform",
        default="amazon_electronics_2018",
        help="写入 platform 列（例如 amazon_home_kitchen_2018）",
    )
    parser.add_argument(
        "--source",
        default="amazon_review_2018_5core",
        help="写入 source 列",
    )
    parser.add_argument(
        "--prepend-summary",
        action="store_true",
        help="正文为「summary. reviewText」（与 Fine Food 导入脚本 --prepend-summary 一致）",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=0,
        help="仅处理前 N 行（0 表示全部，调试用）",
    )
    args = parser.parse_args()

    inp = Path(args.input)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "id",
        "platform",
        "product_id",
        "raw_text",
        "analysis_input_en",
        "lang",
        "created_at",
        "source",
        "label_sentiment",
    ]

    n_in = 0
    n_out = 0
    n_skip = 0

    with open_maybe_gzip(inp) as fin, out.open("w", encoding="utf-8", newline="") as fout:
        writer = csv.DictWriter(fout, fieldnames=fieldnames)
        writer.writeheader()

        for line in fin:
            if args.max_rows and n_out >= args.max_rows:
                break
            n_in += 1
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                n_skip += 1
                continue

            body = build_body(obj, args.prepend_summary)
            if not body:
                n_skip += 1
                continue

            label = overall_to_label(obj.get("overall"))
            if label is None:
                n_skip += 1
                continue

            ts = int(obj.get("unixReviewTime") or 0)
            row = {
                "id": make_review_id(obj),
                "platform": args.platform,
                "product_id": str(obj.get("asin", "")).strip(),
                "raw_text": body,
                "analysis_input_en": body,
                "lang": "en",
                "created_at": ts,
                "source": args.source,
                "label_sentiment": label,
            }
            writer.writerow(row)
            n_out += 1

            if n_in % 500_000 == 0:
                print(f"读入 {n_in} 行 JSON，写出 {n_out} 行，跳过 {n_skip} …", file=sys.stderr)

    print(f"完成：读 JSON 行 {n_in}，写出 {n_out}，跳过 {n_skip}")
    print(f"输出：{out.resolve()}")


if __name__ == "__main__":
    main()
