"""从已有 train/val/test CSV 各抽取一定比例（默认 10%），分层抽样保持标签比例。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))
_COMMON_DIR = _SCRIPT_DIR.parents[1] / "common"
if str(_COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(_COMMON_DIR))
from csv_splits import read_split_csv


def stratified_subset(df: pd.DataFrame, label_col: str, fraction: float, seed: int) -> pd.DataFrame:
    if label_col not in df.columns:
        raise KeyError(f"缺少标签列 {label_col!r}，当前列: {list(df.columns)}")
    if not 0 < fraction <= 1:
        raise ValueError("fraction 须在 (0, 1] 内")
    if len(df) == 0:
        return df.copy()
    try:
        sub, _ = train_test_split(
            df,
            train_size=fraction,
            random_state=seed,
            stratify=df[label_col],
        )
    except ValueError as e:
        raise ValueError(
            "分层抽样失败：标签列含缺失或某类样本过少，无法 stratify。"
            f" 原始错误: {e}"
        ) from e
    return sub.reset_index(drop=True)


def main() -> None:
    p = argparse.ArgumentParser(
        description="对 train/val/test 三个 split 各做分层抽样，写入新目录（不覆盖原文件）。"
    )
    p.add_argument(
        "--input-dir",
        type=Path,
        default=Path("ml/sentiment/data/splits"),
        help="含 train.csv / val.csv / test.csv 的目录",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path("ml/sentiment/data/splits_10pct"),
        help="输出目录（将创建）",
    )
    p.add_argument(
        "--fraction",
        type=float,
        default=0.1,
        help="每个 split 保留比例，默认 0.1（一成）",
    )
    p.add_argument(
        "--label-column",
        default="label_sentiment",
        help="分层依据列名（默认与契约一致）",
    )
    p.add_argument("--seed", type=int, default=42, help="随机种子")
    args = p.parse_args()

    inp: Path = args.input_dir
    out: Path = args.output_dir
    label_col = args.label_column
    frac = args.fraction

    for name in ("train.csv", "val.csv", "test.csv"):
        src = inp / name
        if not src.is_file():
            raise FileNotFoundError(f"找不到: {src}")

    out.mkdir(parents=True, exist_ok=True)

    for name in ("train.csv", "val.csv", "test.csv"):
        src = inp / name
        df = read_split_csv(src)
        sub = stratified_subset(df, label_col, frac, args.seed)
        dst = out / name
        sub.to_csv(dst, index=False)
        print(f"{name}: {len(df)} -> {len(sub)} 行 -> {dst}")

    print(f"完成。训练时使用配置中的 data 路径指向: {out}")


if __name__ == "__main__":
    main()
