"""
句向量微调（MultipleNegativesRankingLoss）：同 BERTopic 主题 id 视为正样本对，
使嵌入空间更贴合电商评论域，再用于第二轮 BERTopic 或线上 transform。

依赖：ml/requirements-bertopic.txt（sentence-transformers、torch 等）。

用法（在仓库根目录）：
  python ml/topic_mining/scripts/finetune_topic_embedding.py \\
    --config ml/topic_mining/configs/embedding_finetune_v1.yaml
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

import pandas as pd
import yaml

def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid yaml: {path}")
    return data


def build_pairs(
    df: pd.DataFrame,
    *,
    text_col: str,
    topic_col: str,
    skip_topics: set[int],
    positives_per_anchor: int,
    max_pairs: int,
    seed: int,
) -> list[tuple[str, str]]:
    rng = random.Random(seed)
    texts_by_topic: dict[int, list[str]] = {}
    for _, row in df.iterrows():
        t_raw = row[topic_col]
        try:
            tid = int(float(t_raw))
        except (TypeError, ValueError):
            continue
        if tid in skip_topics:
            continue
        s = str(row[text_col] or "").strip()
        if len(s) < 2:
            continue
        texts_by_topic.setdefault(tid, []).append(s)

    pairs: list[tuple[str, str]] = []
    for tid, texts in texts_by_topic.items():
        if len(texts) < 2:
            continue
        for anchor in texts:
            others = [x for x in texts if x != anchor]
            if not others:
                continue
            for _ in range(positives_per_anchor):
                pairs.append((anchor, rng.choice(others)))
                if len(pairs) >= max_pairs:
                    return pairs
    rng.shuffle(pairs)
    return pairs[:max_pairs]


def main() -> None:
    p = argparse.ArgumentParser(description="Fine-tune SentenceTransformer with MNRL (same-topic pairs).")
    p.add_argument("--config", required=True, help="embedding_finetune yaml path")
    args = p.parse_args()

    cfg = load_yaml(Path(args.config))
    csv_path = Path(cfg["training_csv"])
    if not csv_path.is_file():
        raise FileNotFoundError(
            f"缺少训练表: {csv_path}\n"
            "请先跑一轮 BERTopic，导出带 topic 列的 CSV（与 text 列），路径与 yaml 中 training_csv 一致。"
        )

    text_col = cfg["text_column"]
    topic_col = cfg["topic_column"]
    base = cfg["base_embedding_model"]
    out_dir = Path(cfg["output_dir"])
    skip_raw = cfg.get("skip_topic_ids") or [-1]
    skip_topics = {int(x) for x in skip_raw}

    df = pd.read_csv(csv_path, encoding="utf-8", encoding_errors="replace")
    for c in (text_col, topic_col):
        if c not in df.columns:
            raise ValueError(f"CSV 缺少列 {c!r}，当前: {list(df.columns)}")

    pairs = build_pairs(
        df,
        text_col=text_col,
        topic_col=topic_col,
        skip_topics=skip_topics,
        positives_per_anchor=int(cfg.get("positives_per_anchor", 1)),
        max_pairs=int(cfg.get("max_pairs", 200_000)),
        seed=int(cfg.get("random_seed", 42)),
    )
    if len(pairs) < 32:
        raise ValueError(
            f"有效正样本对过少 ({len(pairs)})。请检查 topic 列、是否全是 -1、或增大语料。"
        )

    try:
        from sentence_transformers import InputExample, SentenceTransformer, losses
        from torch.utils.data import DataLoader
    except ImportError as e:
        raise SystemExit(
            "未安装 sentence-transformers / torch。请: pip install -r ml/requirements-bertopic.txt"
        ) from e

    model_path = base
    if Path(base).is_dir():
        model_path = str(Path(base).resolve())

    model = SentenceTransformer(model_path, trust_remote_code=True)

    examples = [InputExample(texts=[a, b]) for a, b in pairs]
    batch_size = int(cfg.get("batch_size", 32))
    train_dataloader = DataLoader(examples, shuffle=True, batch_size=batch_size)
    train_loss = losses.MultipleNegativesRankingLoss(model)

    epochs = int(cfg.get("epochs", 2))
    steps_per_epoch = max(1, len(train_dataloader))
    warmup_ratio = float(cfg.get("warmup_ratio", 0.1))
    warmup_steps = int(epochs * steps_per_epoch * warmup_ratio)

    out_dir.parent.mkdir(parents=True, exist_ok=True)

    use_fit = hasattr(model, "fit")
    if use_fit:
        model.fit(
            train_objectives=[(train_dataloader, train_loss)],
            epochs=epochs,
            warmup_steps=warmup_steps,
            optimizer_params={"lr": float(cfg.get("learning_rate", 2e-5))},
            output_path=str(out_dir),
            show_progress_bar=True,
        )
    else:
        # sentence-transformers 3+ 推荐 Trainer；此处兜底提示
        raise RuntimeError(
            "当前 sentence-transformers 版本不支持 SentenceTransformer.fit。"
            "请安装 sentence-transformers 2.x（含 fit），或改用官方 SentenceTransformerTrainer 示例改写本脚本。"
        )

    print(f"Saved: {out_dir.resolve()}")
    print("下一步: 将 run_bertopic / Notebook 中的 embedding 设为该目录，再跑第二轮 BERTopic。")


if __name__ == "__main__":
    main()
