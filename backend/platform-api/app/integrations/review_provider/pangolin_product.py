"""
Pangolin Amazon Scrape API：amzProductDetail（与评论接口同 host，积点 1/次）。
文档示例：https://docs.pangolinfo.com/cn-api-reference/amazonApi/amazonScrapeAPI
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import Settings

from .errors import ReviewProviderError
from .pangolin import _extract_result_rows


def _pick_price_display(prod: dict[str, Any]) -> str | None:
    for k in (
        "price",
        "currentPrice",
        "listPrice",
        "productPrice",
        "buyingPrice",
        "formattedPrice",
        "dealPrice",
        "price_display",
    ):
        v = prod.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    attrs = prod.get("attributes")
    if isinstance(attrs, list):
        for a in attrs:
            if not isinstance(a, dict):
                continue
            key = str(a.get("key") or "").lower()
            if "price" in key:
                val = a.get("value")
                if val is not None and str(val).strip():
                    s = str(val).strip()
                    if any(sym in s for sym in ("$", "¥", "£", "€")) or (s[:1].isdigit() if s else False):
                        return s
    return None


def _pick_main_image(prod: dict[str, Any]) -> str | None:
    img = prod.get("image")
    if img is not None and str(img).strip():
        return str(img).strip()
    hi = prod.get("highResolutionImages")
    if isinstance(hi, list) and hi:
        first = hi[0]
        if first is not None and str(first).strip():
            return str(first).strip()
    thumbs = prod.get("galleryThumbnails")
    if isinstance(thumbs, list) and thumbs:
        first = thumbs[0]
        if first is not None and str(first).strip():
            return str(first).strip()
    return None


def product_dict_to_snapshot(prod: dict[str, Any]) -> dict[str, Any]:
    title = prod.get("title")
    title_s = str(title).strip() if title is not None else ""
    price = _pick_price_display(prod)
    image_url = _pick_main_image(prod)
    return {
        "title": title_s or None,
        "image_url": image_url,
        "price_display": price,
        "asin": str(prod["asin"]).strip() if prod.get("asin") else None,
        "source": "pangolin_amzProductDetail",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def parse_pangolin_product_detail_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    """从 /api/v1/scrape 响应中解析第一条商品详情（非评论行）。"""
    rows = _extract_result_rows(payload)
    if not rows:
        return None
    prod = rows[0]
    if not isinstance(prod, dict):
        return None
    # 评论行通常含 content/reviewId；商品详情含 asin + title 等
    if prod.get("reviewId") or prod.get("review_id"):
        return None
    if not prod.get("title") and not prod.get("image") and not prod.get("asin"):
        return None
    return product_dict_to_snapshot(prod)


def fetch_pangolin_product_snapshot(
    platform: str,
    product_id: str,
    *,
    settings: Settings,
) -> dict[str, Any] | None:
    """
    调用 amzProductDetail；成功返回可写入 product_snapshot 的字典，失败抛 ReviewProviderError。
    """
    token = (settings.pangolin_token or "").strip()
    if not token:
        raise ReviewProviderError(
            "REVIEW_PROVIDER_NOT_CONFIGURED",
            "PANGOLIN_TOKEN 未配置",
        )
    pl = platform.strip().lower()
    if pl != "amazon":
        raise ReviewProviderError(
            "REVIEW_PROVIDER_HTTP_ERROR",
            f"商品详情抓取当前仅支持 platform=amazon，收到 {platform!r}",
        )
    asin = product_id.strip()
    if not asin:
        raise ReviewProviderError("REVIEW_PROVIDER_HTTP_ERROR", "product_id 为空")

    base = (settings.pangolin_base_url or "https://scrapeapi.pangolinfo.com").rstrip("/")
    scrape_url = f"{base}/api/v1/scrape"
    amazon_base = (settings.pangolin_amazon_url or "https://www.amazon.com").rstrip("/")
    dp_url = f"{amazon_base}/dp/{asin}"
    zipcode = (settings.pangolin_product_zipcode or "10041").strip() or "10041"

    body: dict[str, Any] = {
        "url": dp_url,
        "format": "json",
        "parserName": (settings.pangolin_product_parser_name or "amzProductDetail").strip(),
        "bizContext": {"zipcode": zipcode},
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    timeout_sec = max(30.0, float(settings.pangolin_timeout_seconds))
    client_timeout = httpx.Timeout(timeout_sec, connect=30.0)

    try:
        with httpx.Client(timeout=client_timeout) as client:
            resp = client.post(scrape_url, json=body, headers=headers)
    except httpx.TimeoutException as e:
        raise ReviewProviderError("REVIEW_PROVIDER_TIMEOUT", str(e) or "Pangolin 商品详情超时") from e
    except httpx.RequestError as e:
        raise ReviewProviderError(
            "REVIEW_PROVIDER_HTTP_ERROR",
            str(e) or "连接 Pangolin 失败",
        ) from e

    if resp.status_code in (429, 500, 502, 503, 504):
        raise ReviewProviderError(
            "REVIEW_PROVIDER_TRANSIENT",
            f"Pangolin 商品详情 HTTP {resp.status_code}: {resp.text[:500]}",
        )
    if resp.status_code >= 400:
        raise ReviewProviderError(
            "REVIEW_PROVIDER_HTTP_ERROR",
            f"Pangolin 商品详情 HTTP {resp.status_code}: {resp.text[:800]}",
        )

    try:
        payload = resp.json()
    except ValueError as e:
        raise ReviewProviderError(
            "REVIEW_PROVIDER_PARSE_ERROR",
            f"Pangolin 商品详情响应非 JSON：{e!s}",
        ) from e

    if not isinstance(payload, dict):
        raise ReviewProviderError("REVIEW_PROVIDER_PARSE_ERROR", "Pangolin 商品详情响应应为 JSON 对象")

    api_code = payload.get("code")
    if api_code != 0:
        msg = payload.get("message") or str(api_code)
        raise ReviewProviderError(
            "REVIEW_PROVIDER_HTTP_ERROR",
            f"Pangolin 商品详情业务错误 code={api_code}: {msg}",
        )

    snap = parse_pangolin_product_detail_payload(payload)
    return snap


def try_fetch_pangolin_product_snapshot_optional(
    platform: str,
    product_id: str,
    *,
    settings: Settings,
) -> dict[str, Any] | None:
    """不抛错：供拉评流水线在商品详情失败时仍继续抓评论。"""
    try:
        return fetch_pangolin_product_snapshot(platform, product_id, settings=settings)
    except ReviewProviderError:
        return None
