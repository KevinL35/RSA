"""
从 Supabase 读取「三分类总表」review_analysis + reviews 正文，按情感
（positive / negative / neutral）分别跑 BERTopic，将主题写入：
  topic_pool_highlight / topic_pool_pain / topic_pool_observation

两种模式：
  1. 单任务：传 --insight-task-id <UUID>，仅用该任务下的评论；
  2. 全局：不传 --insight-task-id，跨所有任务在三个总表上挖掘（platform/product_id 写为 '_all'）。

依赖：pip install -r ml/requirements-bertopic.txt 与 pip install "supabase>=2,<3"
环境：SUPABASE_URL、SUPABASE_SERVICE_ROLE_KEY（与 platform-api 一致）

用法（仓库根目录）：
  export SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=...
  # 单任务
  python ml/topic_mining/scripts/bertopic_supabase_pools.py \\
    --insight-task-id <UUID> --embedding-model ml/all-MiniLM-L6-v2
  # 全局（三总表）
  python ml/topic_mining/scripts/bertopic_supabase_pools.py \\
    --embedding-model ml/all-MiniLM-L6-v2
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from postgrest.exceptions import APIError

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


_PAGE_SIZE = 1000


def _execute_with_retry(builder: Any, *, retries: int = 3, backoff_sec: float = 1.5):
    """对 Supabase/PostgREST 请求做轻量重试，缓解偶发 TLS/网络抖动。"""
    last_err: Exception | None = None
    for i in range(retries):
        try:
            return builder.execute()
        except Exception as e:  # noqa: BLE001
            last_err = e
            if i >= retries - 1:
                raise
            sleep_s = backoff_sec * (2**i)
            print(f"[topic-mining] supabase request failed, retry {i + 1}/{retries - 1} in {sleep_s:.1f}s: {e}")
            time.sleep(sleep_s)
    if last_err is not None:
        raise last_err
    raise RuntimeError("unreachable")


def _fetch_review_analysis_rows(
    sb: Any, insight_task_id: str | None
) -> list[dict[str, Any]]:
    """分页拉 review_analysis（仅六维未命中且未主题挖掘过）。"""
    out: list[dict[str, Any]] = []
    start = 0
    use_topic_processed_filter = True
    while True:
        q = sb.table("review_analysis").select(
            "id,review_id,sentiment_label,platform,product_id"
        )
        if insight_task_id is not None:
            q = q.eq("insight_task_id", insight_task_id)
        q = q.eq("dimension_match_status", "unmatched").is_("topic_mining_processed_at", "null")
        end = start + _PAGE_SIZE - 1
        try:
            res = _execute_with_retry(q.range(start, end))
        except APIError as e:
            # 向后兼容：若数据库尚未执行 022 迁移，则退化为“仅按 unmatched 过滤”。
            msg = str(getattr(e, "message", "") or e)
            if use_topic_processed_filter and ("topic_mining_processed_at" in msg or "42703" in msg):
                use_topic_processed_filter = False
                q = sb.table("review_analysis").select("id,review_id,sentiment_label,platform,product_id")
                if insight_task_id is not None:
                    q = q.eq("insight_task_id", insight_task_id)
                q = q.eq("dimension_match_status", "unmatched")
                res = _execute_with_retry(q.range(start, end))
            else:
                raise
        rows = res.data or []
        out.extend(rows)
        if len(rows) < _PAGE_SIZE:
            break
        start += _PAGE_SIZE
    return out


def _fetch_reviews_text_by_ids(sb: Any, review_ids: list[str]) -> dict[str, str]:
    id_to_text: dict[str, str] = {}
    chunk = 200
    for i in range(0, len(review_ids), chunk):
        part = review_ids[i : i + chunk]
        rv = _execute_with_retry(sb.table("reviews").select("id,raw_text").in_("id", part))
        for row in rv.data or []:
            id_to_text[str(row["id"])] = str(row.get("raw_text") or "").strip()
    return id_to_text


def fetch_task_corpus(
    sb: Any, insight_task_id: str | None
) -> tuple[str, str, dict[str, list[str]], dict[str, list[str]]]:
    """返回 platform, product_id, {sentiment_label: [doc, ...]}。
    全局模式（insight_task_id=None）下 platform/product_id 固定为 '_all'。"""
    rows = _fetch_review_analysis_rows(sb, insight_task_id)
    if not rows:
        target = insight_task_id or "<global>"
        raise SystemExit(f"review_analysis 无数据：target={target}")

    if insight_task_id is None:
        platform = "_all"
        product_id = "_all"
    else:
        platform = str(rows[0]["platform"])
        product_id = str(rows[0]["product_id"])

    rids = [str(r["review_id"]) for r in rows]
    id_to_text = _fetch_reviews_text_by_ids(sb, rids)

    buckets: dict[str, list[str]] = {"positive": [], "negative": [], "neutral": []}
    analysis_ids_by_bucket: dict[str, list[str]] = {"positive": [], "negative": [], "neutral": []}
    for r in rows:
        lab = str(r.get("sentiment_label") or "neutral").lower()
        if lab not in buckets:
            lab = "neutral"
        rid = str(r["review_id"])
        t = id_to_text.get(rid, "")
        if not t:
            t = " "
        buckets[lab].append(t)
        ra_id = str(r.get("id") or "").strip()
        if ra_id:
            analysis_ids_by_bucket[lab].append(ra_id)
    return platform, product_id, buckets, analysis_ids_by_bucket


def _build_bertopic(
    docs: list[str],
    embedding_model: Any,
    cfg: dict[str, Any],
) -> Any:
    import umap
    from bertopic import BERTopic
    from sklearn.feature_extraction.text import CountVectorizer

    n_docs = len(docs)
    if n_docs < 3:
        raise ValueError(f"文档数过少（{n_docs}），至少需要 3 条有效评论文本才能跑 BERTopic")
    # yaml 里的 min_topic_size 往往按「大任务」调；单 ASIN / 小桶时必须压到 < n_docs，否则全是噪声簇或 0 主题
    min_topic_size_cfg = int(cfg.get("min_topic_size", 10))
    min_topic_size = max(2, min(min_topic_size_cfg, n_docs - 1))
    nr_topics = cfg.get("nr_topics")
    if nr_topics is not None:
        nr_topics = int(nr_topics)

    n_neighbors = min(15, max(2, n_docs - 1))
    n_components = min(5, max(2, n_docs - 1))
    # BERTopic 在 _c_tf_idf 阶段会把「每个主题」当成一条文档；min_df>1 时主题数一少就会触发
    # ValueError: max_df corresponds to < documents than min_df。小样本统一用 min_df=1 更稳。
    vectorizer_model = CountVectorizer(
        min_df=1,
        max_df=1.0,
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
    insight_task_id: str | None,
    embedding_model_ref: str,
    config_path: Path,
    encode_batch_size: int,
    batch_id: str | None,
    dry_run: bool,
    min_bucket_docs: int,
) -> dict[str, Any]:
    cfg = load_yaml(config_path)
    sb = _require_supabase()

    platform, product_id, buckets, analysis_ids_by_bucket = fetch_task_corpus(sb, insight_task_id)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if batch_id is None:
        batch_id = (
            f"global:{ts}" if insight_task_id is None else f"task:{insight_task_id}:{ts}"
        )
    bid = batch_id

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
        "scope": "task" if insight_task_id else "global",
        "platform": platform,
        "product_id": product_id,
        "pools": {},
    }

    mapping = [
        ("positive", "highlight", buckets["positive"]),
        ("negative", "pain", buckets["negative"]),
        ("neutral", "observation", buckets["neutral"]),
    ]
    processed_analysis_ids: set[str] = set()

    for sentiment_label, table_kind, docs in mapping:
        if len(docs) < min_bucket_docs:
            summary["pools"][sentiment_label] = {
                "skipped": True,
                "n_docs": len(docs),
                "reason": f"文档数 < {min_bucket_docs}",
            }
            continue
        table_name = {
            "highlight": "topic_pool_highlight",
            "pain": "topic_pool_pain",
            "observation": "topic_pool_observation",
        }[table_kind]
        try:
            tm = _build_bertopic(docs, embedding_model, cfg)
            tm.fit_transform(docs)
            rows = _topic_rows_for_pool(
                tm,
                batch_id=bid,
                platform=platform,
                product_id=product_id,
                source_sentiment=sentiment_label,
            )
        except Exception as e:  # noqa: BLE001
            summary["pools"][sentiment_label] = {
                "skipped": False,
                "n_docs": len(docs),
                "table": table_name,
                "n_topics": 0,
                "error": str(e)[:800],
            }
            continue
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
            _execute_with_retry(sb.table(table_name).insert(rows))
        processed_analysis_ids.update(analysis_ids_by_bucket.get(sentiment_label, []))

    if not dry_run and processed_analysis_ids:
        now = datetime.now(timezone.utc).isoformat()
        ids = sorted(processed_analysis_ids)
        chunk = 200
        try:
            for i in range(0, len(ids), chunk):
                part = ids[i : i + chunk]
                _execute_with_retry(
                    sb.table("review_analysis")
                    .update({"topic_mining_processed_at": now, "topic_mining_batch_id": bid})
                    .in_("id", part)
                )
            summary["processed_review_analysis"] = len(ids)
        except APIError as e:
            # 向后兼容：未迁移时允许主题挖掘成功，只是暂不回写“已处理”标记。
            msg = str(getattr(e, "message", "") or e)
            if "topic_mining_processed_at" in msg or "topic_mining_batch_id" in msg or "42703" in msg:
                summary["processed_review_analysis"] = 0
                summary["processed_review_analysis_skipped_reason"] = "missing_topic_mining_columns"
            else:
                raise

    return summary


def main() -> None:
    p = argparse.ArgumentParser(description="BERTopic + 写入主题三池（Supabase）")
    p.add_argument(
        "--insight-task-id",
        default=None,
        help="insight_tasks.id（UUID）；省略时跨所有任务对三个总表全局挖掘",
    )
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
        default=8,
        help="单情感桶至少多少条才跑 BERTopic（与 min_topic_size 配合；默认 8 便于单任务小样本）",
    )
    args = p.parse_args()

    os.chdir(_REPO_ROOT)
    summary = run_job(
        insight_task_id=(args.insight_task_id.strip() or None) if args.insight_task_id else None,
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
