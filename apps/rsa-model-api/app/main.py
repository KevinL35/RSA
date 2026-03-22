"""
RSA Model API（TA-11）：POST /analyze
请求体与 apps/api 调用分析源时一致；响应为 { "reviews": [...] }。
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI
from pydantic import Field
from pydantic import BaseModel

from .pipeline import analyze_reviews_body, reset_patterns_cache

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("rsa.model_api")

app = FastAPI(title="RSA Model API", version="0.1.0")


class AnalyzeRequest(BaseModel):
    model_config = {"extra": "allow"}

    insight_task_id: str | None = None
    platform: str | None = None
    product_id: str | None = None
    analysis_provider_id: str | None = None
    dictionary_vertical_id: str | None = None
    reviews: list[dict] = Field(default_factory=list)


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "rsa-model-api"}


@app.post("/analyze")
def analyze(req: AnalyzeRequest) -> dict:
    tax = os.environ.get("TAXONOMY_YAML")
    tax_path = Path(tax) if tax else None
    items = analyze_reviews_body(
        req.model_dump(),
        taxonomy_path=tax_path,
    )
    return {
        "reviews": items,
        "_analysis_provider": "rsa-model-api-v1",
    }


@app.post("/admin/reload-taxonomy")
def reload_taxonomy() -> dict:
    """开发时重载词典；生产可禁用或加鉴权。"""
    reset_patterns_cache()
    return {"ok": True}
