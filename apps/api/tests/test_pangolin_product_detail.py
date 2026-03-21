"""Pangolin amzProductDetail 响应 → product_snapshot 解析。"""

from app.integrations.review_provider.pangolin_product import (
    parse_pangolin_product_detail_payload,
    product_dict_to_snapshot,
)


def test_product_dict_to_snapshot_picks_image_and_title() -> None:
    snap = product_dict_to_snapshot(
        {
            "asin": "B0TEST1234",
            "title": "Example Product",
            "image": "https://m.media-amazon.com/images/I/xxxxx._AC_SL1500_.jpg",
            "price": "$19.99",
        }
    )
    assert snap["title"] == "Example Product"
    assert snap["image_url"] and "media-amazon" in snap["image_url"]
    assert snap["price_display"] == "$19.99"
    assert snap["asin"] == "B0TEST1234"


def test_parse_payload_skips_review_row() -> None:
    payload = {
        "code": 0,
        "data": {
            "json": [
                {
                    "code": 0,
                    "data": {
                        "results": [
                            {
                                "content": "review text",
                                "reviewId": "R1",
                                "title": "Great",
                            }
                        ]
                    },
                }
            ],
        },
    }
    assert parse_pangolin_product_detail_payload(payload) is None


def test_parse_payload_product_shape() -> None:
    payload = {
        "code": 0,
        "data": {
            "json": [
                {
                    "code": 0,
                    "data": {
                        "results": [
                            {
                                "asin": "B0DYTF8L2W",
                                "title": "Sofa",
                                "image": "https://m.media-amazon.com/images/I/main.jpg",
                            }
                        ]
                    },
                }
            ],
        },
    }
    snap = parse_pangolin_product_detail_payload(payload)
    assert snap is not None
    assert snap["asin"] == "B0DYTF8L2W"
    assert snap["title"] == "Sofa"
    assert snap["image_url"] == "https://m.media-amazon.com/images/I/main.jpg"
