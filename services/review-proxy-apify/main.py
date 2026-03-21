"""
TB-2 薄代理：接收 RSA 同款 POST body，调用 Apify run-sync-get-dataset-items，返回 RSA 可解析的 items。
"""

from __future__ import annotations

import os
import secrets
from typing import Any
from urllib.parse import quote

import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="review-proxy-apify", version="1.0.0")

APIFY_TOKEN = (os.environ.get("APIFY_TOKEN") or "").strip()
APIFY_ACTOR_ID = (os.environ.get("APIFY_ACTOR_ID") or "").strip()
APIFY_INPUT_STYLE = (os.environ.get("APIFY_INPUT_STYLE") or "asins").strip().lower()
APIFY_MAX_REVIEWS = int(os.environ.get("APIFY_MAX_REVIEWS") or "50")
APIFY_RUN_TIMEOUT_SECONDS = float(os.environ.get("APIFY_RUN_TIMEOUT_SECONDS") or "240")
PROXY_API_KEY = (os.environ.get("REVIEW_PROXY_API_KEY") or "").strip()


class FetchBody(BaseModel):
    platform: str = Field(..., min_length=1)
    product_id: str = Field(..., min_length=1)


def _require_config() -> None:
    if not APIFY_TOKEN or not APIFY_ACTOR_ID:
        raise HTTPException(
            status_code=500,
            detail="Missing APIFY_TOKEN or APIFY_ACTOR_ID",
        )


def _check_incoming_bearer(authorization: str | None) -> None:
    if not PROXY_API_KEY:
        return
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authorization Bearer required")
    got = authorization[7:].strip()
    if not secrets.compare_digest(got, PROXY_API_KEY):
        raise HTTPException(status_code=403, detail="Invalid API key")


def _build_apify_input(platform: str, product_id: str) -> dict[str, Any]:
    pl = platform.strip().lower()
    if pl != "amazon":
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported platform: {platform!r} (only amazon supported)",
        )
    asin = product_id.strip()
    if not asin:
        raise HTTPException(status_code=400, detail="Empty product_id")
    n = max(1, min(APIFY_MAX_REVIEWS, 500))
    if APIFY_INPUT_STYLE == "producturls":
        return {
            "productUrls": [{"url": f"https://www.amazon.com/dp/{asin}"}],
            "maxReviews": n,
        }
    if APIFY_INPUT_STYLE != "asins":
        raise HTTPException(
            status_code=500,
            detail="APIFY_INPUT_STYLE must be asins or productUrls",
        )
    return {"asins": [asin], "maxReviews": n}


def _first_text(item: dict[str, Any]) -> str | None:
    for key in (
        "reviewText",
        "text",
        "reviewDescription",
        "reviewBody",
        "body",
        "review",
        "content",
    ):
        v = item.get(key)
        if v is not None and str(v).strip():
            return str(v).strip()
    return None


def _map_item(item: dict[str, Any]) -> dict[str, Any] | None:
    raw = _first_text(item)
    if not raw:
        return None
    ext = item.get("id") or item.get("reviewId") or item.get("review_id")
    rating = item.get("rating") or item.get("stars") or item.get("reviewRating")
    title = item.get("title") or item.get("reviewTitle")
    reviewed = item.get("date") or item.get("reviewDate") or item.get("created_at")
    out: dict[str, Any] = {"raw_text": raw}
    if ext is not None:
        out["external_review_id"] = str(ext)
    if title is not None and str(title).strip():
        out["title"] = str(title).strip()
    if reviewed is not None:
        out["reviewed_at"] = str(reviewed)
    if rating is not None:
        try:
            out["rating"] = float(rating)
        except (TypeError, ValueError):
            pass
    return out


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/fetch")
def fetch_reviews(
    body: FetchBody,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> dict[str, Any]:
    _require_config()
    _check_incoming_bearer(authorization)
    actor_path = quote(APIFY_ACTOR_ID, safe="")
    url = f"https://api.apify.com/v2/acts/{actor_path}/run-sync-get-dataset-items"
    timeout_sec = max(1.0, min(APIFY_RUN_TIMEOUT_SECONDS, 300.0))
    apify_input = _build_apify_input(body.platform, body.product_id)
    headers = {"Authorization": f"Bearer {APIFY_TOKEN}"}
    params: dict[str, Any] = {"timeout": timeout_sec}
    client_timeout = httpx.Timeout(timeout_sec + 60.0, connect=30.0)
    with httpx.Client(timeout=client_timeout) as client:
        r = client.post(url, params=params, json=apify_input, headers=headers)

    if r.status_code not in (200, 201):
        try:
            err = r.json()
        except Exception:
            err = {"raw": r.text[:2000]}
        raise HTTPException(
            status_code=502,
            detail={"apify_status": r.status_code, "apify_error": err},
        )

    try:
        payload = r.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Invalid JSON from Apify: {e}") from e

    if not isinstance(payload, list):
        raise HTTPException(
            status_code=502,
            detail="Expected Apify response to be a JSON array of items",
        )

    items: list[dict[str, Any]] = []
    for row in payload:
        if isinstance(row, dict):
            m = _map_item(row)
            if m:
                items.append(m)

    return {"items": items, "source": "apify", "platform": body.platform.strip().lower()}
