"""Pangolin 响应解析（与官方文档示例结构对齐）。"""

from unittest.mock import MagicMock

import pytest

from app.core.config import Settings
from app.integrations.review_provider.pangolin import (
    _extract_result_rows,
    _map_pangolin_review,
    fetch_reviews_via_pangolin,
)


def _ok_review_payload() -> dict:
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "json": [
                {
                    "code": 0,
                    "data": {
                        "results": [
                            {
                                "date": "2026-01-13",
                                "star": "5.0",
                                "title": "Ok",
                                "content": "Recovered after degrade.",
                                "reviewId": "RTEST504",
                            }
                        ]
                    },
                    "message": "ok",
                }
            ],
            "url": "https://www.amazon.com",
            "taskId": "t",
        },
    }


def test_fetch_degrades_page_count_on_gateway_504(monkeypatch: pytest.MonkeyPatch) -> None:
    """504 时减半 pageCount 再请求，避免单次页数过大触发 Cloudflare origin 超时。"""
    import app.integrations.review_provider.pangolin as pangolin_mod

    seen_pages: list[int] = []

    def fake_post(
        *,
        url: str,
        body: dict,
        headers: dict,
        timeout: object,
        attempts: int,
    ):
        pc = int(body["bizContext"]["pageCount"])
        seen_pages.append(pc)
        r = MagicMock()
        if pc >= 8:
            r.status_code = 504
            r.text = "504 gateway"
            return r
        r.status_code = 200
        r.json = lambda: _ok_review_payload()
        return r

    monkeypatch.setattr(pangolin_mod, "_post_pangolin_json", fake_post)

    settings = Settings(
        pangolin_token="test-token",
        pangolin_page_count=10,
        pangolin_page_count_max=10,
        pangolin_timeout_seconds=60.0,
        review_fetch_max_retries=1,
    )
    rows = fetch_reviews_via_pangolin("amazon", "B012345678", settings=settings)
    assert seen_pages == [10, 5]
    assert len(rows) == 1
    assert rows[0]["external_review_id"] == "RTEST504"


def test_extract_and_map_sample_shape() -> None:
    payload = {
        "code": 0,
        "message": "ok",
        "data": {
            "json": [
                {
                    "code": 0,
                    "data": {
                        "results": [
                            {
                                "date": "2026-01-13",
                                "star": "5.0",
                                "title": "Perfect",
                                "content": "Great coat.",
                                "reviewId": "R1IIVEFNGPSLW3",
                            }
                        ]
                    },
                    "message": "ok",
                }
            ],
            "url": "https://www.amazon.com",
            "taskId": "x",
        },
    }
    rows = _extract_result_rows(payload)
    assert len(rows) == 1
    m = _map_pangolin_review(rows[0])
    assert m is not None
    assert m["raw_text"] == "Great coat."
    assert m["external_review_id"] == "R1IIVEFNGPSLW3"
    assert m["title"] == "Perfect"
    assert m["rating"] == 5.0
    assert m["reviewed_at"] == "2026-01-13"
