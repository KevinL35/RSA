"""
Analysis Engine（TA-11）：POST /analyze
请求体与 backend/platform-api 调用分析源时一致；响应为 { "reviews": [...] }。
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import Field
from pydantic import BaseModel

from .pipeline import analyze_reviews_body, reset_patterns_cache

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("rsa.analysis_api")

app = FastAPI(title="Analysis API", version="0.1.0")


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
    # 便于排查：若此处无 taxonomy_empty_seed_ok，多为旧进程未重启（曾要求 seed 非空）。
    return {
        "ok": True,
        "service": "analysis-engine",
        "taxonomy_empty_seed_ok": True,
    }


@app.post("/analyze")
def analyze(req: AnalyzeRequest) -> dict:
    tax = os.environ.get("TAXONOMY_YAML")
    tax_path = Path(tax) if tax else None
    try:
        items = analyze_reviews_body(
            req.model_dump(),
            taxonomy_path=tax_path,
        )
    except RuntimeError as e:
        # 多为缺 SUPABASE_*、词典读取失败等；用 400 避免 API 将配置错误当成可重试的 5xx
        log.warning("analyze failed: %s", e)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        log.exception("analyze failed")
        raise HTTPException(status_code=500, detail=str(e)) from e
    return {
        "reviews": items,
        "_analysis_provider": "analysis-engine-v1",
    }


@app.post("/admin/reload-taxonomy")
def reload_taxonomy() -> dict:
    """开发时重载词典；生产可禁用或加鉴权。"""
    reset_patterns_cache()
    return {"ok": True}
