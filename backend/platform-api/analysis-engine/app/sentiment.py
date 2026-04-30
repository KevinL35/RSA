"""情感：优先 RoBERTa checkpoint；否则用星级或轻量启发式。"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any

log = logging.getLogger(__name__)

_SENTIMENT_ORDER = ("negative", "neutral", "positive")


def sentiment_from_rating(rating: float | None) -> tuple[str, float | None]:
    if rating is None or not isinstance(rating, (int, float)):
        return "neutral", None
    r = float(rating)
    if r <= 2.0:
        return "negative", 0.85
    if r >= 4.0:
        return "positive", 0.85
    return "neutral", 0.7


def sentiment_heuristic(text: str) -> tuple[str, float | None]:
    t = (text or "").lower()
    neg = ("terrible", "awful", "worst", "waste", "refund", "broke", "defective", "horrible", "not worth")
    pos = ("great", "excellent", "love", "perfect", "amazing", "highly recommend", "five stars", "solid")
    n = sum(1 for w in neg if w in t)
    p = sum(1 for w in pos if w in t)
    if n > p and n > 0:
        return "negative", min(0.55 + 0.1 * n, 0.95)
    if p > n and p > 0:
        return "positive", min(0.55 + 0.1 * p, 0.95)
    return "neutral", None


@lru_cache(maxsize=1)
def _load_roberta():
    path = (os.environ.get("SENTIMENT_MODEL_DIR") or "").strip()
    if not path:
        return None
    from pathlib import Path

    p = Path(path)
    if not p.is_dir():
        log.warning("SENTIMENT_MODEL_DIR is not a directory: %s", path)
        return None
    try:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
    except ImportError as e:
        log.warning("transformers/torch not installed, skip RoBERTa: %s", e)
        return None
    tok = AutoTokenizer.from_pretrained(str(p))
    model = AutoModelForSequenceClassification.from_pretrained(str(p))
    model.eval()
    return tok, model


def sentiment_roberta(text: str, max_length: int = 256) -> tuple[str, float | None]:
    loaded = _load_roberta()
    if loaded is None:
        return "", None
    tokenizer, model = loaded
    import torch

    t = (text or "").strip()
    if not t:
        return "neutral", None
    enc = tokenizer(
        t,
        truncation=True,
        max_length=max_length,
        return_tensors="pt",
    )
    with torch.no_grad():
        out = model(**enc)
        logits = out.logits[0]
        probs = torch.softmax(logits, dim=-1)
        idx = int(torch.argmax(probs).item())
        conf = float(probs[idx].item())
    # 与 TA-1 及训练数据一致：0=negative, 1=neutral, 2=positive
    if 0 <= idx < len(_SENTIMENT_ORDER):
        return _SENTIMENT_ORDER[idx], conf
    return "neutral", conf


def predict_sentiment(raw_text: str, rating: float | None) -> tuple[str, float | None]:
    label, conf = sentiment_roberta(raw_text)
    if label:
        return label, conf
    label2, c2 = sentiment_from_rating(rating)
    if c2 is not None:
        return label2, c2
    return sentiment_heuristic(raw_text)
