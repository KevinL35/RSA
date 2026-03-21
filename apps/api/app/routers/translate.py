"""TB-11：可选翻译代理；未配置时不阻断前端。"""

from __future__ import annotations

import httpx
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.rbac import get_rsa_role

router = APIRouter(prefix="/api/v1", tags=["translate"])


class TranslateBody(BaseModel):
    text: str = Field(..., min_length=1, max_length=8000)
    target: str = "zh-CN"


class TranslateOut(BaseModel):
    configured: bool
    translated: str | None = None


@router.post("/translate", response_model=TranslateOut)
def translate_text(
    body: TranslateBody,
    _rbac: Annotated[str, Depends(get_rsa_role)],
) -> TranslateOut:
    settings = get_settings()
    if not settings.translation_api_url:
        return TranslateOut(configured=False, translated=None)
    target = "zh" if body.target.lower().startswith("zh") else "en"
    payload = {
        "q": body.text,
        "source": "en",
        "target": target,
        "format": "text",
    }
    headers: dict[str, str] = {}
    if settings.translation_api_key:
        headers["Authorization"] = f"Bearer {settings.translation_api_key}"
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.post(settings.translation_api_url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
    except Exception:
        return TranslateOut(configured=False, translated=None)
    if isinstance(data, dict):
        out = data.get("translatedText") or data.get("translated") or data.get("data")
        if isinstance(out, str) and out.strip():
            return TranslateOut(configured=True, translated=out)
    return TranslateOut(configured=False, translated=None)
