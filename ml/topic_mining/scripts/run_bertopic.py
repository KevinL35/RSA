"""
命令行运行 BERTopic（非必须依赖 Notebook）。
embedding 可为 Hub 名或本地目录（如 finetune_topic_embedding.py 产出路径）。

用法（仓库根目录）：
  python ml/topic_mining/scripts/run_bertopic.py \\
    --config ml/topic_mining/configs/bertopic_run_v1.yaml \\
    --data-csv ml/topic_mining/data/topic_subsets/topic_input_30k_seed42.csv \\
    --embedding-model models/topic_embedding/bge-mnrl-after-bertopic-r1
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import yaml


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid yaml: {path}")
    return data


def main() -> None:
    p = argparse.ArgumentParser(description="Run BERTopic with configurable embedding model.")
    p.add_argument("--config", required=True, help="bertopic_run_*.yaml")
    p.add_argument("--data-csv", required=True, help="含文本列的 CSV")
    p.add_argument("--text-column", default="analysis_input_en")
    p.add_argument(
        "--embedding-model",
        default=None,
        help="覆盖 yaml 的 embedding_model；可为 Hub 名或本地 SentenceTransformer 目录",
    )
    p.add_argument("--artifact-dir", default=None, help="保存 BERTopic 产物目录（默认 ml/topic_mining/artifacts/...）")
    p.add_argument("--report-dir", default=None, help="导出 topic_info / meta JSON（默认 ml/topic_mining/reports）")
    p.add_argument(
        "--merged-output",
        default=None,
        help="写出带 topic 列的 CSV 路径（默认 report_dir/doc_topics_for_embedding_finetune.csv）",
    )
    p.add_argument(
        "--encode-batch-size",
        type=int,
        default=64,
        help="SentenceTransformer encode 批大小（显存不足可调小，如 16）",
    )
    args = p.parse_args()

    cfg = load_yaml(Path(args.config))
    emb_name = args.embedding_model or cfg.get("embedding_model")
    if not emb_name:
        raise SystemExit("请在 yaml 中配置 embedding_model 或传入 --embedding-model")

    try:
        import torch
        from bertopic import BERTopic
        from sentence_transformers import SentenceTransformer
        from sklearn.feature_extraction.text import CountVectorizer
        import umap
    except ImportError as e:
        raise SystemExit("请安装: pip install -r ml/requirements-bertopic.txt") from e

    data_csv = Path(args.data_csv)
    if not data_csv.is_file():
        raise FileNotFoundError(data_csv)

    df = pd.read_csv(data_csv, encoding="utf-8", encoding_errors="replace")
    tc = args.text_column
    if tc not in df.columns:
        raise ValueError(f"缺少列 {tc!r}，当前: {list(df.columns)}")
    s = df[tc].astype(str).str.strip()
    df = df[s != ""].copy().reset_index(drop=True)
    docs = df[tc].tolist()

    n_docs = len(docs)
    if n_docs < 3:
        raise ValueError(f"非空文本过少（{n_docs}），BERTopic/UMAP 至少需要数条以上样本。")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print("torch.cuda.is_available():", torch.cuda.is_available(), "| encode device:", device)
    local = Path(emb_name)
    emb_arg = str(local.resolve()) if local.is_dir() else emb_name
    embedding_model = SentenceTransformer(emb_arg, device=device, trust_remote_code=True)

    _encode_orig = embedding_model.encode

    def encode_normalized(sentences, **kwargs):
        kwargs.setdefault("batch_size", args.encode_batch_size)
        kwargs.setdefault("normalize_embeddings", True)
        kwargs.setdefault("show_progress_bar", True)
        return _encode_orig(sentences, **kwargs)

    embedding_model.encode = encode_normalized

    min_topic_size = int(cfg.get("min_topic_size", 10))
    if min_topic_size >= n_docs:
        raise ValueError(
            f"min_topic_size（{min_topic_size}）必须小于文档条数（{n_docs}），请改 yaml 或换更大语料。"
        )
    nr_topics = cfg.get("nr_topics")
    if nr_topics is not None:
        nr_topics = int(nr_topics)

    # UMAP：n_neighbors < n_samples；n_components 不宜 ≥ n_samples
    n_neighbors = min(15, max(2, n_docs - 1))
    n_components = min(5, max(2, n_docs - 1))
    min_df = 2 if n_docs >= 20 else 1

    vectorizer_model = CountVectorizer(
        min_df=min_df,
        ngram_range=(1, 2),
        stop_words="english",
    )
    umap_model = umap.UMAP(
        n_neighbors=n_neighbors,
        n_components=n_components,
        min_dist=0.0,
        metric="cosine",
        random_state=42,
    )
    topic_model = BERTopic(
        embedding_model=embedding_model,
        vectorizer_model=vectorizer_model,
        umap_model=umap_model,
        min_topic_size=min_topic_size,
        nr_topics=nr_topics,
        calculate_probabilities=bool(cfg.get("calculate_probabilities", False)),
        verbose=bool(cfg.get("verbose", True)),
    )

    topics, _ = topic_model.fit_transform(docs)

    report_dir = Path(args.report_dir or "ml/topic_mining/reports")
    artifact_dir = Path(
        args.artifact_dir or f"ml/topic_mining/artifacts/bertopic_cli_{cfg.get('version', 'v1')}"
    )
    report_dir.mkdir(parents=True, exist_ok=True)
    artifact_dir.parent.mkdir(parents=True, exist_ok=True)

    info = topic_model.get_topic_info()
    topic_csv = report_dir / "bertopic_topic_info.csv"
    info.to_csv(topic_csv, index=False)
    print("topic_info ->", topic_csv)

    out = df.copy()
    out["topic"] = topics
    merged = Path(args.merged_output) if args.merged_output else report_dir / "doc_topics_for_embedding_finetune.csv"
    merged.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(merged, index=False)
    print("含 topic 列，供下一轮 MNRL 微调: ->", merged)

    topic_model.save(
        str(artifact_dir),
        serialization="safetensors",
        save_ctfidf=True,
        save_embedding_model=False,
    )
    meta = {
        "data_csv": str(data_csv),
        "n_rows": len(df),
        "text_column": tc,
        "embedding_model": emb_name,
        "device": device,
        "encode_batch_size": args.encode_batch_size,
        "umap": {"n_neighbors": n_neighbors, "n_components": n_components, "random_state": 42},
        "count_vectorizer_min_df": min_df,
        "min_topic_size": min_topic_size,
        "artifact_dir": str(artifact_dir),
        "n_topic_ids": int(len(set(topics))),
        "doc_topics_csv": str(merged),
        "note": "UMAP/HDBSCAN 多在 CPU 上跑；仅句向量 encode 占用 GPU。加载已保存模型时需传入同一 embedding。",
    }
    meta_path = report_dir / "bertopic_run_meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print("meta ->", meta_path)
    print("model saved ->", artifact_dir)


if __name__ == "__main__":
    main()
