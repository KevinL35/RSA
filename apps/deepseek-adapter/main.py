"""
DeepSeek ↔ RSA platform-api 的 TB-3 协议适配层。

运行：
  cd apps/deepseek-adapter && pip install -r requirements.txt
  export DEEPSEEK_API_KEY=sk-... && uvicorn main:app --host 0.0.0.0 --port 9100

platform-api .env：
  ANALYSIS_PROVIDER_URL=http://127.0.0.1:9100/analyze
  ANALYSIS_PROVIDER_API_KEY=<与 ADAPTER_SHARED_SECRET 相同，若配置了的话>

Agent 补洞（可选，同一进程）：
  AGENT_ENRICHMENT_URL=http://127.0.0.1:9100/agent-enrich
"""

from __future__ import annotations

import json
import re
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from openai import OpenAI
from pydantic_settings import BaseSettings, SettingsConfigDict

app = FastAPI(title="RSA DeepSeek TB-3 Adapter", version="0.1.0")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-reasoner"
    deepseek_max_reviews_per_call: int = 25
    adapter_shared_secret: str = ""
    adapter_host: str = "0.0.0.0"
    adapter_port: int = 9100


def get_settings() -> Settings:
    return Settings()


SYSTEM_PROMPT = """You are an e-commerce review analyst. For each review, output structured JSON only.

Rules:
- sentiment.label must be one of: negative, neutral, positive. Include confidence 0-1 if possible.
- dimensions: array of hits from these six keys ONLY: pros, cons, return_reasons, purchase_motivation, user_expectation, usage_scenario.
- Each dimension object: dimension (string), keywords (array of short English phrases, 1-3 words each), evidence_quote (short excerpt from the review text, same language as review), highlight_spans optional (start/end UTF-16 or byte-agnostic offsets are not required — use [] if unsure).
- Use only dimensions that truly apply; omit empty dimensions or use empty keywords [] if none.
- Output MUST be a single JSON object with key "reviews" whose value is an array aligned to the input review ids in order.
- Each element: {"review_id": "<uuid>", "sentiment": {"label": "...", "confidence": 0.0}, "dimensions": [...]}

No markdown fences. No commentary outside JSON."""


def _auth_ok(authorization: str | None, secret: str) -> bool:
    if not (secret or "").strip():
        return True
    exp = f"Bearer {secret.strip()}"
    return (authorization or "").strip() == exp


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    obj = json.loads(text)
    if not isinstance(obj, dict):
        raise ValueError("top level not object")
    return obj


def _call_deepseek_batch(
    client: OpenAI,
    model: str,
    batch: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    lines = []
    for r in batch:
        rid = r.get("id")
        title = (r.get("title") or "").strip()
        body = (r.get("raw_text") or "").strip()
        rating = r.get("rating")
        lines.append(
            json.dumps(
                {"review_id": str(rid), "title": title, "rating": rating, "text": body[:8000]},
                ensure_ascii=False,
            )
        )
    user_content = (
        "Analyze these reviews (JSON lines, one review per line).\n"
        + "\n".join(lines)
        + '\n\nReturn JSON: {"reviews":[...]} with the same review_id values and in the same order.'
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.2,
    )
    msg = resp.choices[0].message.content
    if not msg:
        raise ValueError("empty model response")
    payload = _extract_json_object(msg)
    raw_list = payload.get("reviews")
    if not isinstance(raw_list, list):
        raise ValueError("missing reviews array")
    return [x for x in raw_list if isinstance(x, dict)]


def _run_tb3_body(body: dict[str, Any], authorization: str | None) -> dict[str, Any]:
    s = get_settings()
    if not (s.deepseek_api_key or "").strip():
        raise HTTPException(status_code=503, detail="DEEPSEEK_API_KEY not set")
    if not _auth_ok(authorization, s.adapter_shared_secret):
        raise HTTPException(status_code=401, detail="Unauthorized")

    reviews = body.get("reviews") or []
    if not isinstance(reviews, list) or not reviews:
        return {"reviews": []}

    client = OpenAI(
        api_key=s.deepseek_api_key.strip(),
        base_url=s.deepseek_base_url.strip().rstrip("/"),
    )
    model = s.deepseek_model.strip() or "deepseek-reasoner"
    chunk = max(1, min(50, int(s.deepseek_max_reviews_per_call or 25)))

    out_items: list[dict[str, Any]] = []
    for i in range(0, len(reviews), chunk):
        batch = reviews[i : i + chunk]
        if not all(isinstance(x, dict) for x in batch):
            continue
        part = _call_deepseek_batch(client, model, batch)
        # align by review_id from batch
        by_id = {str(x.get("review_id") or x.get("id") or ""): x for x in part}
        for r in batch:
            rid = str(r.get("id", ""))
            item = by_id.get(rid)
            if item:
                item.setdefault("review_id", rid)
                out_items.append(item)
            else:
                out_items.append(
                    {
                        "review_id": rid,
                        "sentiment": {"label": "neutral", "confidence": None},
                        "dimensions": [],
                    }
                )

    return {"reviews": out_items, "_adapter": "deepseek", "_model": model}


@app.post("/analyze")
async def analyze(request: Request, authorization: str | None = Header(default=None)) -> dict:
    """与 platform-api TB-3 分析源相同请求体。"""
    try:
        body = await request.json()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"invalid json: {e!s}") from e
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="body must be object")
    return _run_tb3_body(body, authorization)


@app.post("/agent-enrich")
async def agent_enrich(request: Request, authorization: str | None = Header(default=None)) -> dict:
    """与 platform-api Agent 增强相同请求体（子集 reviews + enrichment_mode）。"""
    try:
        body = await request.json()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"invalid json: {e!s}") from e
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="body must be object")
    return _run_tb3_body(body, authorization)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
