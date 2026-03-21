"""Pangolin 响应解析（与官方文档示例结构对齐）。"""

from app.integrations.review_provider.pangolin import _extract_result_rows, _map_pangolin_review


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
