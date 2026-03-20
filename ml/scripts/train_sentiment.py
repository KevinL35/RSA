import argparse
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


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def tokenize_fn(examples, tokenizer, text_column, max_length: int):
    return tokenizer(
        examples[text_column],
        truncation=True,
        max_length=max_length,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Fine-tune RoBERTa for sentiment.")
    parser.add_argument("--config", required=True, help="Path to train_roberta yaml.")
    args = parser.parse_args()

    cfg = load_yaml(Path(args.config))
    model_cfg = cfg["model"]
    data_cfg = cfg["data"]
    train_cfg = cfg["training"]
    eval_cfg = cfg.get("evaluation", {})

    cleaned_csv = Path(data_cfg["cleaned_csv"])
    train_csv = Path(data_cfg["train_csv"])
    val_csv = Path(data_cfg["val_csv"])
    test_csv = Path(data_cfg["test_csv"])

    required = [train_csv, val_csv, test_csv]
    for p in required:
        if not p.exists():
            raise FileNotFoundError(f"Missing split file: {p}. Run split_dataset.py first.")

    df_train = pd.read_csv(train_csv)
    df_val = pd.read_csv(val_csv)
    df_test = pd.read_csv(test_csv)

    text_col = data_cfg["text_column"]
    label_col = data_cfg["label_column"]

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

    ds_train = ds_train.map(_tokenize, batched=True)
    ds_val = ds_val.map(_tokenize, batched=True)
    ds_test = ds_test.map(_tokenize, batched=True)

    # Trainer expects "labels"
    ds_train = ds_train.rename_column(label_col, "labels")
    ds_val = ds_val.rename_column(label_col, "labels")
    ds_test = ds_test.rename_column(label_col, "labels")

    ds_train = ds_train.remove_columns([c for c in ds_train.column_names if c not in ["input_ids", "attention_mask", "labels", "token_type_ids"]])
    ds_val = ds_val.remove_columns([c for c in ds_val.column_names if c not in ["input_ids", "attention_mask", "labels", "token_type_ids"]])
    ds_test = ds_test.remove_columns([c for c in ds_test.column_names if c not in ["input_ids", "attention_mask", "labels", "token_type_ids"]])

    collator = DataCollatorWithPadding(tokenizer=tokenizer)

    accuracy_metric = evaluate.load("accuracy")

    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        preds = np.argmax(logits, axis=-1)
        acc = accuracy_metric.compute(predictions=preds, references=labels)
        return {"accuracy": acc["accuracy"]}

    output_dir = Path(train_cfg["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        learning_rate=train_cfg["learning_rate"],
        num_train_epochs=train_cfg["num_train_epochs"],
        per_device_train_batch_size=train_cfg["per_device_train_batch_size"],
        per_device_eval_batch_size=train_cfg["per_device_eval_batch_size"],
        weight_decay=train_cfg["weight_decay"],
        logging_steps=train_cfg["logging_steps"],
        evaluation_strategy=train_cfg["eval_strategy"],
        save_strategy=train_cfg["save_strategy"],
        metric_for_best_model=train_cfg["metric_for_best_model"],
        greater_is_better=train_cfg["greater_is_better"],
        seed=train_cfg["seed"],
        load_best_model_at_end=True,
        report_to=[],
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=ds_train,
        eval_dataset=ds_val,
        tokenizer=tokenizer,
        data_collator=collator,
        compute_metrics=compute_metrics,
    )

    trainer.train()

    # Evaluate on test split and write minimal report
    test_metrics = trainer.evaluate(eval_dataset=ds_test)
    report_path = Path(eval_cfg.get("report_output", "reports/sentiment_eval.json"))
    report_path.parent.mkdir(parents=True, exist_ok=True)
    pd.Series(test_metrics).to_json(report_path)

    print(f"Test metrics: {test_metrics}")


if __name__ == "__main__":
    main()

