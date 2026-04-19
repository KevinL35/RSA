"""
从 Supabase 读取某 insight 任务下「三分类总表」review_analysis + reviews 正文，
按情感（positive / negative / neutral）分别跑 BERTopic，将主题写入：
  topic_pool_highlight / topic_pool_pain / topic_pool_observation

依赖：pip install -r ml/requirements-bertopic.txt 与 pip install "supabase>=2,<3"
环境：SUPABASE_URL、SUPABASE_SERVICE_ROLE_KEY（与 platform-api 一致）

用法（仓库根目录）：
  export SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=...
  python ml/topic_mining/scripts/bertopic_supabase_pools.py \\
    --insight-task-id <UUID> \\
    --embedding-model ml/all-MiniLM-L6-v2
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

# 仓库根：.../ml/topic_mining/scripts -> parents[3]
_REPO_ROOT = Path(__file__).resolve().parents[3]


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid yaml: {path}")
    return data


def _require_supabase():
    try:
        from supabase import create_client
    except ImportError as e:
        raise SystemExit("请安装: pip install 'supabase>=2,<3'") from e
    url = (os.environ.get("SUPABASE_URL") or "").strip()
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not url or not key:
        raise SystemExit("请设置环境变量 SUPABASE_URL 与 SUPABASE_SERVICE_ROLE_KEY")
    return create_client(url, key)


def fetch_task_corpus(sb: Any, insight_task_id: str) -> tuple[str, str, dict[str, list[str]]]:
    """返回 platform, product_id, {sentiment_label: [doc, ...]}。"""
    ra = (
        sb.table("review_analysis")
        .select("review_id,sentiment_label,platform,product_id")
        .eq("insight_task_id", insight_task_id)
        .execute()
    )
    rows = ra.data or []
    if not rows:
        raise SystemExit(f"review_analysis 无数据：insight_task_id={insight_task_id}")

    platform = str(rows[0]["platform"])
    product_id = str(rows[0]["product_id"])
    rids = [str(r["review_id"]) for r in rows]
    # reviews 分批 in_ 查询（避免 URL 过长）
    id_to_text: dict[str, str] = {}
    chunk = 200
    for i in range(0, len(rids), chunk):
        part = rids[i : i + chunk]
        rv = sb.table("reviews").select("id,raw_text").in_("id", part).execute()
        for row in rv.data or []:
            id_to_text[str(row["id"])] = str(row.get("raw_text") or "").strip()

    buckets: dict[str, list[str]] = {"positive": [], "negative": [], "neutral": []}
    for r in rows:
        lab = str(r.get("sentiment_label") or "neutral").lower()
        if lab not in buckets:
            lab = "neutral"
        rid = str(r["review_id"])
        t = id_to_text.get(rid, "")
        if not t:
            t = " "
        buckets[lab].append(t)
    return platform, product_id, buckets


def _build_bertopic(
    docs: list[str],
    embedding_model: Any,
    cfg: dict[str, Any],
) -> Any:
    import umap
    from bertopic import BERTopic
    from sklearn.feature_extraction.text import CountVectorizer

    n_docs = len(docs)
    min_topic_size = int(cfg.get("min_topic_size", 10))
    if min_topic_size >= n_docs:
        raise ValueError(f"min_topic_size（{min_topic_size}）>= 文档数（{n_docs}）")
    nr_topics = cfg.get("nr_topics")
    if nr_topics is not None:
        nr_topics = int(nr_topics)

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
    return BERTopic(
        embedding_model=embedding_model,
        vectorizer_model=vectorizer_model,
        umap_model=umap_model,
        min_topic_size=min_topic_size,
        nr_topics=nr_topics,
        calculate_probabilities=bool(cfg.get("calculate_probabilities", False)),
        verbose=bool(cfg.get("verbose", False)),
    )


def _topic_rows_for_pool(
    topic_model: Any,
    *,
    batch_id: str,
    platform: str,
    product_id: str,
    source_sentiment: str,
) -> list[dict[str, Any]]:
    """从已 fit 的 topic_model 生成写入 topic_pool_* 的行。"""
    info = topic_model.get_topic_info()
    rows: list[dict[str, Any]] = []
    topic_col = "Topic" if "Topic" in info.columns else None
    if topic_col is None:
        for c in info.columns:
            if str(c).lower() == "topic":
                topic_col = c
                break
    if topic_col is None:
        raise RuntimeError(f"get_topic_info 无 Topic 列: {list(info.columns)}")

    for _, r in info.iterrows():
        tid = int(r[topic_col])
        if tid == -1:
            continue
        tw = topic_model.get_topic(tid)
        if not tw:
            canonical = f"topic_{tid}"
            aliases: list[str] = []
        else:
            canonical = str(tw[0][0]).strip() or f"topic_{tid}"
            aliases = [str(x[0]).strip() for x in tw[1:12] if x and str(x[0]).strip()]

        evidence: list[dict[str, str]] = []
        try:
            reps = topic_model.get_representative_docs(tid) or []
            for doc in reps[:4]:
                s = doc if isinstance(doc, str) else str(doc)
                evidence.append({"text": s[:400]})
        except Exception:
            pass

        rows.append(
            {
                "batch_id": batch_id,
                "source_sentiment": source_sentiment,
                "platform": platform,
                "product_id": product_id,
                "source_topic_id": str(tid),
                "suggested_canonical": canonical[:512],
                "aliases": aliases,
                "quality_score": None,
                "evidence_snippets": evidence,
            }
        )
    return rows


def run_job(
    *,
    insight_task_id: str,
    embedding_model_ref: str,
    config_path: Path,
    encode_batch_size: int,
    batch_id: str | None,
    dry_run: bool,
    min_bucket_docs: int,
) -> dict[str, Any]:
    cfg = load_yaml(config_path)
    sb = _require_supabase()

    platform, product_id, buckets = fetch_task_corpus(sb, insight_task_id)

    bid = batch_id or f"task:{insight_task_id}:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

    try:
        import torch
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        raise SystemExit("请安装: pip install -r ml/requirements-bertopic.txt") from e

    emb_path = Path(embedding_model_ref)
    emb_arg = str(emb_path.resolve()) if emb_path.is_dir() else embedding_model_ref
    device = "cuda" if torch.cuda.is_available() else "cpu"
    embedding_model = SentenceTransformer(emb_arg, device=device, trust_remote_code=True)
    _enc = embedding_model.encode

    def encode_norm(sentences, **kwargs):
        kwargs.setdefault("batch_size", encode_batch_size)
        kwargs.setdefault("normalize_embeddings", True)
        kwargs.setdefault("show_progress_bar", True)
        return _enc(sentences, **kwargs)

    embedding_model.encode = encode_norm

    summary: dict[str, Any] = {
        "batch_id": bid,
        "insight_task_id": insight_task_id,
        "platform": platform,
        "product_id": product_id,
        "pools": {},
    }

    mapping = [
        ("positive", "highlight", buckets["positive"]),
        ("negative", "pain", buckets["negative"]),
        ("neutral", "observation", buckets["neutral"]),
    ]

    for sentiment_label, table_kind, docs in mapping:
        if len(docs) < min_bucket_docs:
            summary["pools"][sentiment_label] = {
                "skipped": True,
                "n_docs": len(docs),
                "reason": f"文档数 < {min_bucket_docs}",
            }
            continue
        tm = _build_bertopic(docs, embedding_model, cfg)
        tm.fit_transform(docs)
        table_name = {
            "highlight": "topic_pool_highlight",
            "pain": "topic_pool_pain",
            "observation": "topic_pool_observation",
        }[table_kind]
        rows = _topic_rows_for_pool(
            tm,
            batch_id=bid,
            platform=platform,
            product_id=product_id,
            source_sentiment=sentiment_label,
        )
        summary["pools"][sentiment_label] = {
            "skipped": False,
            "n_docs": len(docs),
            "table": table_name,
            "n_topics": len(rows),
        }
        if dry_run:
            summary["pools"][sentiment_label]["rows_preview"] = rows[:3]
            continue
        if rows:
            sb.table(table_name).insert(rows).execute()

    return summary


def main() -> None:
    p = argparse.ArgumentParser(description="BERTopic + 写入主题三池（Supabase）")
    p.add_argument("--insight-task-id", required=True, help="insight_tasks.id（UUID）")
    p.add_argument(
        "--embedding-model",
        required=True,
        help="SentenceTransformer：Hub 名或本地目录",
    )
    p.add_argument(
        "--config",
        default=str(_REPO_ROOT / "ml/topic_mining/configs/bertopic_run_v1.yaml"),
        help="BERTopic 超参 yaml",
    )
    p.add_argument("--encode-batch-size", type=int, default=64)
    p.add_argument("--batch-id", default=None, help="自定义 batch_id；默认带时间戳")
    p.add_argument("--dry-run", action="store_true", help="只打印摘要，不写库")
    p.add_argument(
        "--min-bucket-docs",
        type=int,
        default=15,
        help="单情感桶至少多少条才跑 BERTopic（需 > min_topic_size）",
    )
    args = p.parse_args()

    os.chdir(_REPO_ROOT)
    summary = run_job(
        insight_task_id=args.insight_task_id.strip(),
        embedding_model_ref=args.embedding_model.strip(),
        config_path=Path(args.config),
        encode_batch_size=args.encode_batch_size,
        batch_id=(args.batch_id.strip() if args.batch_id else None),
        dry_run=args.dry_run,
        min_bucket_docs=args.min_bucket_docs,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
