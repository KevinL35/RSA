import argparse
import inspect
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
import evaluate
from datasets import Dataset
from transformers import AutoModelForSequenceClassification, AutoTokenizer, DataCollatorWithPadding, Trainer, TrainingArguments

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))
from csv_splits import read_split_csv


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _minimal_eval_training_args() -> TrainingArguments:
    """仅用于 Trainer.evaluate，兼容 transformers 4/5。"""
    params = inspect.signature(TrainingArguments.__init__).parameters
    kwargs: dict = {
        "output_dir": "tmp-eval",
        "per_device_eval_batch_size": 32,
        "report_to": [],
    }
    if "eval_strategy" in params:
        kwargs["eval_strategy"] = "no"
    elif "evaluation_strategy" in params:
        kwargs["evaluation_strategy"] = "no"
    allowed = set(params.keys()) - {"self", "kwargs"}
    filtered = {k: v for k, v in kwargs.items() if k in allowed}
    return TrainingArguments(**filtered)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate sentiment model checkpoint on test split.")
    parser.add_argument("--config", required=True, help="Path to train_roberta yaml.")
    parser.add_argument("--checkpoint_dir", required=True, help="Trained model output dir.")
    args = parser.parse_args()

    cfg = load_yaml(Path(args.config))
    model_cfg = cfg["model"]
    data_cfg = cfg["data"]
    eval_cfg = cfg.get("evaluation", {})

    test_csv = Path(data_cfg["test_csv"])
    if not test_csv.exists():
        raise FileNotFoundError(f"Missing split file: {test_csv}")

    df_test = read_split_csv(test_csv)
    text_col = data_cfg["text_column"]
    label_col = data_cfg["label_column"]

    tokenizer = AutoTokenizer.from_pretrained(args.checkpoint_dir)
    model = AutoModelForSequenceClassification.from_pretrained(args.checkpoint_dir)

    ds_test = Dataset.from_pandas(df_test)

    def _tokenize(batch):
        return tokenizer(
            batch[text_col],
            truncation=True,
            max_length=model_cfg["max_length"],
        )

    ds_test = ds_test.map(_tokenize, batched=True)
    ds_test = ds_test.rename_column(label_col, "labels")
    ds_test = ds_test.remove_columns([c for c in ds_test.column_names if c not in ["input_ids", "attention_mask", "labels", "token_type_ids"]])

    collator = DataCollatorWithPadding(tokenizer=tokenizer)
    accuracy_metric = evaluate.load("accuracy")

    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        preds = np.argmax(logits, axis=-1)
        acc = accuracy_metric.compute(predictions=preds, references=labels)
        return {"accuracy": acc["accuracy"]}

    training_args = _minimal_eval_training_args()

    _tc = inspect.signature(Trainer.__init__).parameters
    _trainer_kw = dict(
        model=model,
        args=training_args,
        eval_dataset=ds_test,
        data_collator=collator,
        compute_metrics=compute_metrics,
    )
    if "processing_class" in _tc:
        _trainer_kw["processing_class"] = tokenizer
    else:
        _trainer_kw["tokenizer"] = tokenizer

    trainer = Trainer(**_trainer_kw)

    metrics = trainer.evaluate()
    report_path = Path(eval_cfg.get("report_output", "reports/sentiment_eval.json"))
    report_path.parent.mkdir(parents=True, exist_ok=True)
    pd.Series(metrics).to_json(report_path)
    print(f"Eval metrics: {metrics}")


if __name__ == "__main__":
    main()

