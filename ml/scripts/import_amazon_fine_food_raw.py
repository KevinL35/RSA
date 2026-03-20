#!/usr/bin/env python3
"""
将 Kaggle「Amazon Fine Food Reviews」风格 CSV 转为 finetune 数据契约要求的 reviews.csv。

常见列：Id, ProductId, UserId, ProfileName, HelpfulnessNumerator, HelpfulnessDenominator,
      Score, Time, Summary, Text
情感标签由 Score 映射到 label_sentiment：
  - 1、2 星 -> 0 (negative)
  - 3 星 -> 1 (neutral)
  - 4、5 星 -> 2 (positive)
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """统一列名（忽略大小写、常见拼写差异）。"""
    rename = {}
    for c in df.columns:
        key = str(c).strip().lower().replace(" ", "")
        if key == "id":
            rename[c] = "Id"
        elif key == "productid":
            rename[c] = "ProductId"
        elif key in ("userid",):
            rename[c] = "UserId"
        elif key in ("profilename", "profilenam", "profile_name"):
            rename[c] = "ProfileName"
        elif key in ("helpfulnessnumerator",):
            rename[c] = "HelpfulnessNumerator"
        elif key in ("helpfulnessdenominator",):
            rename[c] = "HelpfulnessDenominator"
        elif key == "score":
            rename[c] = "Score"
        elif key == "time":
            rename[c] = "Time"
        elif key == "summary":
            rename[c] = "Summary"
        elif key == "text":
            rename[c] = "Text"
    return df.rename(columns=rename)


def score_to_sentiment(score: int) -> int:
    s = int(score)
    if s <= 2:
        return 0
    if s == 3:
        return 1
    return 2


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Amazon Fine Food Reviews CSV -> reviews.csv")
    parser.add_argument(
        "--input",
        required=True,
        help="原始 CSV 路径（含 Id, ProductId, Score, Text 等列）",
    )
    parser.add_argument(
        "--output",
        default="finetune/data/raw/reviews.csv",
        help="输出路径（需与 data_contract.yaml 的 raw_input 一致）",
    )
    parser.add_argument(
        "--prepend-summary",
        action="store_true",
        help="若 Summary 非空，则拼成「Summary. Text」作为正文（默认只用 Text）",
    )
    args = parser.parse_args()

    inp = Path(args.input)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(inp)
    df = normalize_columns(df)

    required = {"Id", "ProductId", "Score", "Text"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"缺少必需列（归一化后）: {sorted(missing)}；当前列: {list(df.columns)}")

    text = df["Text"].astype(str).str.strip()
    if args.prepend_summary and "Summary" in df.columns:
        summ = df["Summary"].fillna("").astype(str).str.strip()
        body = summ.where(summ == "", summ + ". ") + text
    else:
        body = text

    out_df = pd.DataFrame(
        {
            "id": df["Id"].astype(str),
            "platform": "amazon_fine_food",
            "product_id": df["ProductId"].astype(str),
            "raw_text": body,
            "analysis_input_en": body,
            "lang": "en",
            "created_at": pd.to_numeric(df["Time"], errors="coerce").fillna(0).astype("int64"),
            "source": "amazon_fine_food_reviews",
            "label_sentiment": df["Score"].apply(score_to_sentiment),
        }
    )

    out_df.to_csv(out, index=False)
    print(f"Rows: {len(out_df)}")
    print(f"Saved: {out.resolve()}")
    print("label_sentiment 分布:")
    print(out_df["label_sentiment"].value_counts().sort_index().to_string())


if __name__ == "__main__":
    main()
