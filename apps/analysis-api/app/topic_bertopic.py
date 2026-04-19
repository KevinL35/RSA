"""
可选：加载离线训练的 BERTopic 目录，对文本做 transform（需与训练时相同的 SentenceTransformer）。

环境变量（均非空时启用）：
  BERTOPIC_MODEL_DIR   仓库内或绝对路径，指向 bertopic save 目录（如 models/topic_mining/rsa-t1/bertopic_cli_1.0.0）
  TOPIC_EMBEDDING_MODEL_DIR  句向量模型目录或 Hub 名（与 run_bertopic.py 训练时一致；save_embedding_model=False 时必填）

可选：
  TOPIC_ENCODE_BATCH_SIZE  默认 32
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

log = logging.getLogger("rsa.analysis_api.topic")

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _resolve_repo_path(p: str) -> Path:
    path = Path(p.strip())
    if not path.is_absolute():
        path = _REPO_ROOT / path
    return path.resolve()


def topic_inference_enabled() -> bool:
    m = (os.environ.get("BERTOPIC_MODEL_DIR") or "").strip()
    e = (os.environ.get("TOPIC_EMBEDDING_MODEL_DIR") or "").strip()
    return bool(m and e)


@lru_cache(maxsize=1)
def _load_stack() -> tuple[Any, Any] | None:
    if not topic_inference_enabled():
        return None
    model_dir = _resolve_repo_path(os.environ["BERTOPIC_MODEL_DIR"])
    emb_arg = os.environ["TOPIC_EMBEDDING_MODEL_DIR"].strip()
    emb_path = Path(emb_arg)
    emb_ref = str(emb_path.resolve()) if emb_path.is_dir() else emb_arg

    if not model_dir.is_dir():
        log.warning("BERTOPIC_MODEL_DIR 不是目录: %s", model_dir)
        return None

    try:
        import torch
        from bertopic import BERTopic
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        log.warning("未安装 bertopic/sentence-transformers，跳过主题推理: %s", e)
        return None

    try:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        embedding_model = SentenceTransformer(emb_ref, device=device, trust_remote_code=True)
        topic_model = BERTopic.load(str(model_dir), embedding_model=embedding_model)
    except Exception as e:
        log.exception("加载 BERTopic 失败: %s", e)
        return None

    return topic_model, embedding_model


def _topic_to_payload(topic_model: Any, tid: int) -> dict[str, Any]:
    outlier = tid == -1
    keywords: list[str] = []
    if not outlier:
        try:
            tw = topic_model.get_topic(tid)
            if tw:
                keywords = [str(w[0]) for w in tw[:8] if w and len(w) > 0]
        except Exception:
            pass
    return {
        "id": int(tid),
        "keywords": keywords,
        "outlier": outlier,
    }


def predict_topics_for_texts(texts: list[str]) -> list[dict[str, Any] | None]:
    """
    与 texts 等长。未启用或加载失败时返回全 None。
    空文本会替换为单空格再编码，避免部分版本报错。
    """
    if not texts:
        return []
    stack = _load_stack()
    if stack is None:
        return [None] * len(texts)

    topic_model, _ = stack
    batch_size = int((os.environ.get("TOPIC_ENCODE_BATCH_SIZE") or "32").strip() or "32")
    batch_size = max(1, min(batch_size, 256))

    docs = []
    for t in texts:
        s = (t or "").strip()
        if not s:
            s = " "
        docs.append(s)

    try:
        topics, _ = topic_model.transform(docs)
    except Exception as e:
        log.exception("BERTopic.transform 失败: %s", e)
        return [None] * len(texts)

    out: list[dict[str, Any] | None] = []
    for tid in topics:
        try:
            tid_i = int(tid)
        except (TypeError, ValueError):
            tid_i = -1
        out.append(_topic_to_payload(topic_model, tid_i))
    return out


def clear_topic_cache() -> None:
    """热重载模型时调用（如实现 admin reload）。"""
    _load_stack.cache_clear()
