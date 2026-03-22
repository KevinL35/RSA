"""TA-9：BERTopic 离线语料预处理（无 bertopic 依赖，便于单测）。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

import pandas as pd
import yaml


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def utc_batch_end_timestamp(iso_date: str | None) -> int:
    """batch_end：某日 00:00:00 UTC。iso_date 形如 YYYY-MM-DD；None 为今天 UTC 午夜。"""
    if iso_date:
        d = datetime.strptime(iso_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        now = datetime.now(timezone.utc)
        d = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(d.timestamp())


def read_corpus_csv(path: Path) -> pd.DataFrame:
    enc_kw: dict[str, Any] = {"encoding": "utf-8", "encoding_errors": "replace"}
    try:
        return pd.read_csv(path, **enc_kw)
    except pd.errors.ParserError:
        return pd.read_csv(path, engine="python", on_bad_lines="skip", **enc_kw)


def normalize_corpus_columns(df: pd.DataFrame) -> pd.DataFrame:
    """统一文本列：text_en 或 analysis_input_en -> _text。"""
    out = df.copy()
    if "text_en" in out.columns:
        out["_text"] = out["text_en"].astype(str)
    elif "analysis_input_en" in out.columns:
        out["_text"] = out["analysis_input_en"].astype(str)
    else:
        raise ValueError("CSV 需包含 text_en 或 analysis_input_en 列（与 TA-8 一致）")

    for col in ("platform", "product_id"):
        if col not in out.columns:
            raise ValueError(f"缺少必填列: {col}")
    return out


def apply_text_constraints(df: pd.DataFrame, min_len: int, max_len: int) -> pd.DataFrame:
    t = df["_text"].str.strip()
    lens = t.str.len()
    return df[(lens >= min_len) & (lens <= max_len)].assign(_text=t)


def dedupe_corpus(df: pd.DataFrame, prefer_keys: list[str]) -> pd.DataFrame:
    """按 prefer_keys 中第一个存在的列去重（通常 id）。"""
    key = next((k for k in prefer_keys if k in df.columns), None)
    if key:
        return df.drop_duplicates(subset=[key], keep="first")
    if "created_at" in df.columns:
        return df.drop_duplicates(subset=["_text", "created_at"], keep="first")
    return df.drop_duplicates(subset=["_text"], keep="first")


def filter_by_time_window(
    df: pd.DataFrame,
    batch_end_ts: int,
    window_days: int,
) -> tuple[pd.DataFrame, bool]:
    """created_at（Unix 秒 UTC）落在 [batch_end - window, batch_end)。"""
    if "created_at" not in df.columns:
        return df, False
    s = pd.to_numeric(df["created_at"], errors="coerce")
    mask = s.notna() & (s >= batch_end_ts - window_days * 86400) & (s < batch_end_ts)
    return df.loc[mask].copy(), True


def iter_slices(
    df: pd.DataFrame,
    key_cols: list[str],
    min_docs: int,
) -> Iterator[tuple[tuple[str, ...], pd.DataFrame]]:
    if df.empty:
        return
    for key, g in df.groupby(list(key_cols), sort=True):
        if isinstance(key, str):
            key_t = (key,)
        else:
            key_t = tuple(str(x) for x in key)
        if len(g) >= min_docs:
            yield key_t, g.reset_index(drop=True)


def topic_quality_score(topic_count: int, top_ctfidf: float, max_count_in_run: int) -> float:
    """0–100 启发式质量分：规模 + 代表词强度（TA-1 口径下的可解释 proxy，非学术 coherence）。"""
    denom = max(max_count_in_run, 1)
    size_norm = min(1.0, topic_count / max(0.45 * denom, 40.0))
    strength_norm = min(1.0, top_ctfidf / 0.07) if top_ctfidf > 0 else 0.0
    return round(100.0 * (0.42 * size_norm + 0.58 * strength_norm), 2)


def candidate_record(
    *,
    batch_id: str,
    platform: str,
    product_id: str,
    source_topic_id: str,
    suggested_canonical: str,
    aliases: list[str],
    quality_score: float,
    quality_components: dict[str, Any],
    evidence_snippets: list[str],
) -> dict[str, Any]:
    """供人工复核的候选行（写入 JSONL）。dimension_6way 由审核人补全后再走 TA-10。"""
    return {
        "batch_id": batch_id,
        "platform": platform,
        "product_id": product_id,
        "source_topic_id": source_topic_id,
        "suggested_canonical": suggested_canonical,
        "aliases": aliases,
        "quality_score": quality_score,
        "quality_components": quality_components,
        "evidence_snippets": evidence_snippets,
        "dimension_6way": None,
        "reviewer_notes": None,
    }


@dataclass
class RunManifest:
    batch_id: str
    batch_end_ts: int
    window_days: int
    corpus_schema_version: str
    slices: list[dict[str, Any]] = field(default_factory=list)
    skipped: list[dict[str, Any]] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "batch_end_utc": datetime.fromtimestamp(self.batch_end_ts, tz=timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "window_days": self.window_days,
            "corpus_schema_version": self.corpus_schema_version,
            "slices": self.slices,
            "skipped": self.skipped,
        }

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_json(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
