#!/usr/bin/env python3
"""TA-9：按 TA-8 切片策略对语料跑 BERTopic，产出候选 JSONL + 批次 manifest JSON。"""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

import numpy as np

from bertopic_offline_lib import (
    RunManifest,
    append_jsonl,
    apply_text_constraints,
    dedupe_corpus,
    filter_by_time_window,
    iter_slices,
    load_yaml,
    normalize_corpus_columns,
    read_corpus_csv,
    topic_quality_score,
    utc_batch_end_timestamp,
    candidate_record,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def fit_and_extract_topics(
    df_slice: pd.DataFrame,
    *,
    batch_id: str,
    platform: str,
    product_id: str,
    embedding_model: str,
    min_topic_size: int,
    nr_topics: int | None,
    calculate_probabilities: bool,
    verbose: bool,
    max_alias_terms: int,
    max_evidence_snippets: int,
) -> tuple[list[dict], dict]:
    from bertopic import BERTopic
    from sentence_transformers import SentenceTransformer

    docs = df_slice["_text"].astype(str).tolist()
    embedding = SentenceTransformer(embedding_model)
    topic_model = BERTopic(
        embedding_model=embedding,
        min_topic_size=min_topic_size,
        nr_topics=nr_topics,
        calculate_probabilities=calculate_probabilities,
        verbose=verbose,
    )
    topics, _ = topic_model.fit_transform(docs)
    topics_arr = np.asarray(topics)
    info = topic_model.get_topic_info()
    valid = info[info["Topic"] >= 0]
    max_count = int(valid["Count"].max()) if not valid.empty else 1

    candidates: list[dict] = []
    n_outliers = int((topics_arr == -1).sum())

    for _, row in valid.iterrows():
        tid = int(row["Topic"])
        count = int(row["Count"])
        words_scores = topic_model.get_topic(tid) or []
        if not words_scores:
            continue
        top_word, top_score = words_scores[0]
        all_words = [w for w, _ in words_scores[: max_alias_terms + 3]]
        if len(all_words) >= 2:
            suggested_canonical = f"{all_words[0]} {all_words[1]}".strip()
        else:
            suggested_canonical = all_words[0]
        aliases = [w for w in all_words[2 : 2 + max_alias_terms] if w and w != suggested_canonical]

        q = topic_quality_score(count, float(top_score), max_count)

        rep_docs: list[str] = []
        try:
            raw_rep = topic_model.get_representative_docs(tid)
            if raw_rep:
                rep_docs = [str(x) for x in raw_rep[:max_evidence_snippets]]
        except Exception:
            rep_docs = []

        if not rep_docs:
            idxs = [i for i, t in enumerate(topics_arr.tolist()) if int(t) == tid][:max_evidence_snippets]
            rep_docs = [docs[i] for i in idxs]

        candidates.append(
            candidate_record(
                batch_id=batch_id,
                platform=platform,
                product_id=product_id,
                source_topic_id=str(tid),
                suggested_canonical=suggested_canonical,
                aliases=aliases,
                quality_score=q,
                quality_components={
                    "topic_document_count": count,
                    "top_term_ctfidf": round(float(top_score), 6),
                    "max_topic_count_in_slice": max_count,
                },
                evidence_snippets=rep_docs,
            )
        )

    slice_stats = {
        "platform": platform,
        "product_id": product_id,
        "n_docs": len(docs),
        "n_topics": int(len(valid)),
        "n_outliers": n_outliers,
        "n_candidates": len(candidates),
    }
    return candidates, slice_stats


def main() -> int:
    parser = argparse.ArgumentParser(description="TA-9 BERTopic offline discovery.")
    parser.add_argument("--corpus-csv", type=Path, required=True, help="含 text_en 或 analysis_input_en + platform + product_id 的 CSV")
    parser.add_argument(
        "--batch-strategy",
        type=Path,
        default=_repo_root() / "ml/configs/bertopic_batch_strategy_v1.yaml",
    )
    parser.add_argument(
        "--run-config",
        type=Path,
        default=_repo_root() / "ml/configs/bertopic_run_v1.yaml",
    )
    parser.add_argument("--batch-id", default=None, help="不提供则自动生成")
    parser.add_argument("--batch-end", default=None, help="窗口右边界日期 YYYY-MM-DD（UTC 午夜），默认今天 UTC")
    parser.add_argument("--reports-dir", type=Path, default=_repo_root() / "ml/reports")
    parser.add_argument("--platform", default=None, help="仅处理该平台（可选）")
    parser.add_argument("--product-id", default=None, help="仅处理该商品（可选，须与 --platform 同用）")
    parser.add_argument("--dry-run", action="store_true", help="只统计切片与跳过原因，不加载 BERTopic")
    parser.add_argument("--force", action="store_true", help="覆盖已存在的同 batch 输出文件")
    args = parser.parse_args()

    strat = load_yaml(args.batch_strategy)
    run_cfg = load_yaml(args.run_config)

    batch_id = args.batch_id or f"topic-{uuid.uuid4().hex[:12]}"
    batch_end_ts = utc_batch_end_timestamp(args.batch_end)
    window_days = int(strat["window"]["window_days"])
    min_docs = int(strat["slice"]["min_documents_product_slice"])
    key_cols = list(strat["slice"]["primary_keys"])
    tc = strat["text_constraints"]

    manifest_path = args.reports_dir / f"bertopic_run_{batch_id}.json"
    candidates_path = args.reports_dir / f"bertopic_candidates_{batch_id}.jsonl"
    if manifest_path.exists() or candidates_path.exists():
        if not args.force:
            print(f"输出已存在: {manifest_path} 或 {candidates_path}，请加 --force", file=sys.stderr)
            return 2
        if candidates_path.exists():
            candidates_path.unlink()

    df = read_corpus_csv(args.corpus_csv)
    df = normalize_corpus_columns(df)
    df = apply_text_constraints(df, int(tc["min_length"]), int(tc["max_length"]))
    df = dedupe_corpus(df, list(tc["dedupe_keys"]))

    df, had_window = filter_by_time_window(df, batch_end_ts, window_days)
    if not had_window:
        print("警告: CSV 无 created_at，已跳过时间窗口过滤（与 TA-8 不完全一致）", file=sys.stderr)

    if args.platform is not None:
        df = df[df["platform"].astype(str) == str(args.platform)]
    if args.product_id is not None:
        if args.platform is None:
            print("--product-id 需要同时指定 --platform", file=sys.stderr)
            return 2
        df = df[df["product_id"].astype(str) == str(args.product_id)]

    manifest = RunManifest(
        batch_id=batch_id,
        batch_end_ts=batch_end_ts,
        window_days=window_days,
        corpus_schema_version=str(strat.get("corpus_schema_version", "ta8-v1")),
    )

    # 记录未达最小样本的切片
    if not df.empty:
        grouped = df.groupby(key_cols, sort=True)
        for key, g in grouped:
            key_t = (key,) if isinstance(key, str) else tuple(str(x) for x in key)
            if len(g) < min_docs:
                manifest.skipped.append(
                    {
                        "platform": key_t[0],
                        "product_id": key_t[1] if len(key_t) > 1 else "",
                        "reason": "insufficient_n",
                        "n": int(len(g)),
                        "min_documents": min_docs,
                    }
                )

    if args.dry_run:
        for key_t, g in iter_slices(df, key_cols, min_docs):
            manifest.slices.append(
                {
                    "platform": key_t[0],
                    "product_id": key_t[1] if len(key_t) > 1 else "",
                    "n_docs": len(g),
                    "dry_run": True,
                }
            )
        manifest.write(manifest_path)
        print(f"dry-run 已写入 {manifest_path}")
        return 0

    nr_topics = run_cfg.get("nr_topics")
    if nr_topics is not None:
        nr_topics = int(nr_topics)

    for key_t, g in iter_slices(df, key_cols, min_docs):
        platform, product_id = key_t[0], key_t[1] if len(key_t) > 1 else ""
        try:
            cands, stats = fit_and_extract_topics(
                g,
                batch_id=batch_id,
                platform=platform,
                product_id=product_id,
                embedding_model=str(run_cfg["embedding_model"]),
                min_topic_size=int(run_cfg["min_topic_size"]),
                nr_topics=nr_topics,
                calculate_probabilities=bool(run_cfg.get("calculate_probabilities", False)),
                verbose=bool(run_cfg.get("verbose", False)),
                max_alias_terms=int(run_cfg.get("max_alias_terms", 10)),
                max_evidence_snippets=int(run_cfg.get("max_evidence_snippets", 4)),
            )
        except Exception as e:
            manifest.skipped.append(
                {
                    "platform": platform,
                    "product_id": product_id,
                    "reason": "bertopic_failed",
                    "error": str(e),
                    "n": len(g),
                }
            )
            continue

        manifest.slices.append(stats)
        for row in cands:
            append_jsonl(candidates_path, row)

    if not candidates_path.exists():
        candidates_path.write_text("", encoding="utf-8")

    manifest.write(manifest_path)
    print(f"完成 batch_id={batch_id} manifest={manifest_path} candidates={candidates_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
