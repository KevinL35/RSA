import argparse
import glob
import inspect
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
import evaluate
from datasets import Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
)

# 压低 Hub/权重加载时的 LOAD REPORT 等 INFO，避免被误认为报错；Trainer 仍会用 tqdm 打训练进度。
import transformers

transformers.logging.set_verbosity_error()

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))
_COMMON_DIR = _SCRIPT_DIR.parents[1] / "common"
if str(_COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(_COMMON_DIR))
from csv_splits import read_split_csv


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def tokenize_fn(examples, tokenizer, text_column, max_length: int):
    return tokenizer(
        examples[text_column],
        truncation=True,
        max_length=max_length,
    )


def resolve_train_csv_paths(data_cfg: dict) -> list[Path]:
    """Single train.csv, or many shards via train_csv_shards / train_csv_shard_glob."""
    shards = data_cfg.get("train_csv_shards") or []
    glob_pat = data_cfg.get("train_csv_shard_glob")
    if shards and glob_pat:
        raise ValueError("Use only one of train_csv_shards or train_csv_shard_glob, not both.")
    if shards:
        return [Path(p) for p in shards]
    if glob_pat:
        paths = sorted(Path(p) for p in glob.glob(glob_pat))
        if paths:
            return paths
        # e.g. merged to train.csv and removed shards — fall back to single train_csv
        tc = Path(data_cfg["train_csv"])
        if tc.exists():
            print(
                f"Warning: train_csv_shard_glob matched no files ({glob_pat!r}); "
                f"using train_csv: {tc}"
            )
            return [tc]
        raise FileNotFoundError(
            f"No files matched train_csv_shard_glob: {glob_pat!r} and train_csv not found: {tc}"
        )
    return [Path(data_cfg["train_csv"])]


def load_train_dataframe(data_cfg: dict) -> pd.DataFrame:
    paths = resolve_train_csv_paths(data_cfg)
    for p in paths:
        if not p.exists():
            raise FileNotFoundError(f"Missing train file: {p}")
    dfs = [read_split_csv(p) for p in paths]
    df = pd.concat(dfs, ignore_index=True)
    if data_cfg.get("dedupe_train_on_id") and "id" in df.columns:
        n0 = len(df)
        df = df.drop_duplicates(subset=["id"], keep="first")
        dropped = n0 - len(df)
        if dropped:
            print(f"dedupe_train_on_id: removed {dropped} duplicate id row(s)")
    return df


def _narrow_for_training(df: pd.DataFrame, text_col: str, label_col: str) -> pd.DataFrame:
    for c in (text_col, label_col):
        if c not in df.columns:
            raise ValueError(f"Missing column {c!r}; have: {list(df.columns)}")
    return df[[text_col, label_col]].copy()


def coerce_training_cfg(train_cfg: dict) -> dict:
    """PyYAML 常把 2e-5 等读成 str，Torch 优化器要求数值类型。"""
    out = dict(train_cfg)
    for k in ("learning_rate", "weight_decay"):
        if k in out and isinstance(out[k], str):
            out[k] = float(out[k])
    for k in (
        "num_train_epochs",
        "per_device_train_batch_size",
        "per_device_eval_batch_size",
        "logging_steps",
        "seed",
        "gradient_accumulation_steps",
        "dataloader_num_workers",
    ):
        if k in out and isinstance(out[k], str):
            out[k] = int(float(out[k]))
    for k in ("fp16", "bf16", "tf32"):
        if k in out and isinstance(out[k], str):
            out[k] = out[k].strip().lower() in {"1", "true", "yes", "on"}
    return out


def build_training_arguments(train_cfg: dict, output_dir: Path) -> TrainingArguments:
    """兼容 transformers 4.x（evaluation_strategy）与 5.x（eval_strategy）。"""
    train_cfg = coerce_training_cfg(train_cfg)
    params = inspect.signature(TrainingArguments.__init__).parameters
    kwargs: dict = {
        "output_dir": str(output_dir),
        "learning_rate": float(train_cfg["learning_rate"]),
        "num_train_epochs": int(train_cfg["num_train_epochs"]),
        "per_device_train_batch_size": int(train_cfg["per_device_train_batch_size"]),
        "per_device_eval_batch_size": int(train_cfg["per_device_eval_batch_size"]),
        "weight_decay": float(train_cfg["weight_decay"]),
        "logging_steps": int(train_cfg["logging_steps"]),
        "save_strategy": train_cfg["save_strategy"],
        "metric_for_best_model": train_cfg["metric_for_best_model"],
        "greater_is_better": train_cfg["greater_is_better"],
        "seed": int(train_cfg["seed"]),
        "load_best_model_at_end": True,
        "report_to": [],
    }
    # Optional perf/runtime knobs from yaml (only passed when provided)
    optional_keys = (
        "fp16",
        "bf16",
        "tf32",
        "gradient_accumulation_steps",
        "dataloader_num_workers",
    )
    for k in optional_keys:
        if k in train_cfg:
            kwargs[k] = train_cfg[k]
    ev = train_cfg["eval_strategy"]
    if "eval_strategy" in params:
        kwargs["eval_strategy"] = ev
    elif "evaluation_strategy" in params:
        kwargs["evaluation_strategy"] = ev
    else:
        raise RuntimeError(
            "TrainingArguments 不支持 eval_strategy / evaluation_strategy，请升级或降级 transformers。"
        )
    allowed = set(params.keys()) - {"self", "kwargs"}
    filtered = {k: v for k, v in kwargs.items() if k in allowed}
    unknown = set(kwargs) - set(filtered)
    if unknown:
        print(f"Warning: TrainingArguments 忽略未知参数: {sorted(unknown)}")
    return TrainingArguments(**filtered)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fine-tune RoBERTa for sentiment.")
    parser.add_argument("--config", required=True, help="Path to train_roberta yaml.")
    parser.add_argument(
        "--max-train-rows",
        type=int,
        default=None,
        help="Debug: only use first N train rows (reduces RAM).",
    )
    parser.add_argument(
        "--max-val-rows",
        type=int,
        default=None,
        help="Debug: only use first N val rows.",
    )
    parser.add_argument(
        "--max-test-rows",
        type=int,
        default=None,
        help="Debug: only use first N test rows.",
    )
    parser.add_argument(
        "--tokenized-cache-dir",
        type=str,
        default=None,
        help="若目录下已有 train/val/test 子目录则直接加载，跳过耗时的 map；否则在 tokenize 后写入，下次秒开。换数据后请删该目录或加 --force-refresh-tokenized-cache。",
    )
    parser.add_argument(
        "--force-refresh-tokenized-cache",
        action="store_true",
        help="忽略已有 tokenized 缓存，重新 map。",
    )
    args = parser.parse_args()

    cfg = load_yaml(Path(args.config))
    model_cfg = cfg["model"]
    data_cfg = cfg["data"]
    train_cfg = cfg["training"]
    eval_cfg = cfg.get("evaluation", {})

    val_csv = Path(data_cfg["val_csv"])
    test_csv = Path(data_cfg["test_csv"])

    text_col = data_cfg["text_column"]
    label_col = data_cfg["label_column"]

    cache_root = Path(args.tokenized_cache_dir) if args.tokenized_cache_dir else None
    cache_train = cache_root / "train" if cache_root else None
    cache_val = cache_root / "val" if cache_root else None
    cache_test = cache_root / "test" if cache_root else None
    cache_hit = (
        cache_root
        and not args.force_refresh_tokenized_cache
        and cache_train.is_dir()
        and cache_val.is_dir()
        and cache_test.is_dir()
    )
    subset_mode = (
        args.max_train_rows is not None
        or args.max_val_rows is not None
        or args.max_test_rows is not None
    )
    if subset_mode and cache_hit:
        print(
            "试跑模式（--max-*-rows）：忽略已有 tokenized 缓存，避免误把全量缓存当子集或反之。"
        )
    if subset_mode:
        cache_hit = False

    if cache_hit:
        print(f"使用 tokenized 缓存（跳过 map）：{cache_root}")
        ds_train = Dataset.load_from_disk(str(cache_train))
        ds_val = Dataset.load_from_disk(str(cache_val))
        ds_test = Dataset.load_from_disk(str(cache_test))
    else:
        for p in (val_csv, test_csv):
            if not p.exists():
                raise FileNotFoundError(f"Missing split file: {p}. Run split_dataset.py first.")

        df_train = load_train_dataframe(data_cfg)
        df_val = read_split_csv(val_csv)
        df_test = read_split_csv(test_csv)

        if args.max_train_rows is not None:
            df_train = df_train.head(args.max_train_rows)
            print(f"--max-train-rows: using {len(df_train)} train rows")
        if args.max_val_rows is not None:
            df_val = df_val.head(args.max_val_rows)
            print(f"--max-val-rows: using {len(df_val)} val rows")
        if args.max_test_rows is not None:
            df_test = df_test.head(args.max_test_rows)
            print(f"--max-test-rows: using {len(df_test)} test rows")

        df_train = _narrow_for_training(df_train, text_col, label_col)
        df_val = _narrow_for_training(df_val, text_col, label_col)
        df_test = _narrow_for_training(df_test, text_col, label_col)

        for name, frame in ("train", df_train), ("val", df_val), ("test", df_test):
            try:
                frame[label_col] = pd.to_numeric(frame[label_col], errors="raise").astype("int64")
            except (ValueError, TypeError) as e:
                raise ValueError(
                    f"{name} split: 标签列 {label_col!r} 须为可转为整数的类别编号（0..{model_cfg['num_labels'] - 1}），"
                    "请检查 CSV 是否含空值或非数字。"
                ) from e

        tokenizer = AutoTokenizer.from_pretrained(model_cfg["pretrained_name"])
        model = AutoModelForSequenceClassification.from_pretrained(
            model_cfg["pretrained_name"],
            num_labels=model_cfg["num_labels"],
        )

        ds_train = Dataset.from_pandas(df_train)
        ds_val = Dataset.from_pandas(df_val)
        ds_test = Dataset.from_pandas(df_test)

        def _tokenize(batch):
            return tokenize_fn(batch, tokenizer, text_col, model_cfg["max_length"])

        _map_kw = {"batched": True, "num_proc": 1}
        ds_train = ds_train.map(_tokenize, **_map_kw)
        ds_val = ds_val.map(_tokenize, **_map_kw)
        ds_test = ds_test.map(_tokenize, **_map_kw)

        ds_train = ds_train.rename_column(label_col, "labels")
        ds_val = ds_val.rename_column(label_col, "labels")
        ds_test = ds_test.rename_column(label_col, "labels")

        ds_train = ds_train.remove_columns(
            [c for c in ds_train.column_names if c not in ["input_ids", "attention_mask", "labels", "token_type_ids"]]
        )
        ds_val = ds_val.remove_columns(
            [c for c in ds_val.column_names if c not in ["input_ids", "attention_mask", "labels", "token_type_ids"]]
        )
        ds_test = ds_test.remove_columns(
            [c for c in ds_test.column_names if c not in ["input_ids", "attention_mask", "labels", "token_type_ids"]]
        )

        if cache_root and not subset_mode:
            cache_root.mkdir(parents=True, exist_ok=True)
            ds_train.save_to_disk(str(cache_train))
            ds_val.save_to_disk(str(cache_val))
            ds_test.save_to_disk(str(cache_test))
            print(f"已写入 tokenized 缓存，下次可加同一参数跳过 map：{cache_root}")
        elif cache_root and subset_mode:
            print(
                "试跑模式：未写入 tokenized 缓存。全量训练请去掉 --max-*-rows 并保留 --tokenized-cache-dir。"
            )

    if cache_hit:
        tokenizer = AutoTokenizer.from_pretrained(model_cfg["pretrained_name"])
        model = AutoModelForSequenceClassification.from_pretrained(
            model_cfg["pretrained_name"],
            num_labels=model_cfg["num_labels"],
        )

    collator = DataCollatorWithPadding(tokenizer=tokenizer)

    accuracy_metric = evaluate.load("accuracy")

    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        preds = np.argmax(logits, axis=-1)
        acc = accuracy_metric.compute(predictions=preds, references=labels)
        return {"accuracy": acc["accuracy"]}

    output_dir = Path(train_cfg["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    training_args = build_training_arguments(train_cfg, output_dir)

    _tc = inspect.signature(Trainer.__init__).parameters
    _trainer_kw = dict(
        model=model,
        args=training_args,
        train_dataset=ds_train,
        eval_dataset=ds_val,
        data_collator=collator,
        compute_metrics=compute_metrics,
    )
    if "processing_class" in _tc:
        _trainer_kw["processing_class"] = tokenizer
    else:
        _trainer_kw["tokenizer"] = tokenizer

    trainer = Trainer(**_trainer_kw)

    trainer.train()

    # Evaluate on test split and write minimal report
    test_metrics = trainer.evaluate(eval_dataset=ds_test)
    report_path = Path(eval_cfg.get("report_output", "reports/sentiment_eval.json"))
    report_path.parent.mkdir(parents=True, exist_ok=True)
    pd.Series(test_metrics).to_json(report_path)

    print(f"Test metrics: {test_metrics}")


if __name__ == "__main__":
    main()

