import argparse
from pathlib import Path

import pandas as pd
import yaml
from sklearn.model_selection import train_test_split


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
    parser = argparse.ArgumentParser(description="Split cleaned dataset into train/val/test.")
    parser.add_argument("--config", required=True, help="Path to training config yaml.")
    args = parser.parse_args()

    cfg = load_yaml(Path(args.config))
    data_cfg = cfg["data"]

    cleaned = Path(data_cfg["cleaned_csv"])
    label_col = data_cfg["label_column"]
    df = pd.read_csv(cleaned, encoding="utf-8", encoding_errors="replace")
    if label_col not in df.columns:
        raise ValueError(f"cleaned_csv 缺少标签列 {label_col!r}，当前列: {list(df.columns)}")
    split_cfg = data_cfg["split"]

    train_size = split_cfg["train_size"]
    val_size = split_cfg["val_size"]
    test_size = split_cfg["test_size"]
    seed = split_cfg["random_seed"]

    if abs(train_size + val_size + test_size - 1.0) > 1e-8:
        raise ValueError("train_size + val_size + test_size must equal 1.0")

    try:
        train_df, temp_df = train_test_split(
            df,
            test_size=(1 - train_size),
            random_state=seed,
            stratify=df[label_col],
        )
        val_ratio_in_temp = val_size / (val_size + test_size)
        val_df, test_df = train_test_split(
            temp_df,
            test_size=(1 - val_ratio_in_temp),
            random_state=seed,
            stratify=temp_df[label_col],
        )
    except ValueError as e:
        raise ValueError(
            "分层划分失败：请检查标签列是否含缺失值，且每个类别至少有足够样本（极少类或极小集会导致 stratify 失败）。"
            f" 原始错误: {e}"
        ) from e

    for key in ["train_csv", "val_csv", "test_csv"]:
        Path(data_cfg[key]).parent.mkdir(parents=True, exist_ok=True)

    train_df.to_csv(data_cfg["train_csv"], index=False)
    val_df.to_csv(data_cfg["val_csv"], index=False)
    test_df.to_csv(data_cfg["test_csv"], index=False)

    print(f"train: {len(train_df)}, val: {len(val_df)}, test: {len(test_df)}")


if __name__ == "__main__":
    main()
