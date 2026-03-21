"""TB-9/TB-10：对比分析聚合与前置条件"""

from collections import Counter
from unittest.mock import MagicMock

from app.modules.compare.service import (
    _conclusion_cards,
    _delta_map,
    build_product_compare,
)


def test_compare_missing_one_product() -> None:
    sb = MagicMock()
    chain = MagicMock()
    sb.table.return_value = chain
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.execute.side_effect = [
        MagicMock(data=[]),
        MagicMock(data=[{"id": "t2", "platform": "b", "product_id": "p2"}]),
    ]
    out = build_product_compare(
        sb,
        platform_a="a",
        product_id_a="1",
        platform_b="b",
        product_id_b="2",
    )
    assert out["_missing"] is True
    assert out["reasons"] == {"a": "no_success_task", "b": None}
    assert out["products"]["a"]["insight_task_id"] is None
    assert out["products"]["b"]["insight_task_id"] == "t2"


def test_compare_empty_analysis() -> None:
    """成功任务但 review_analysis 为空 → empty_analysis。"""
    sb = MagicMock()
    chain = MagicMock()
    sb.table.return_value = chain
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain

    task_a = {"id": "t1", "platform": "a", "product_id": "p1"}
    task_b = {"id": "t2", "platform": "b", "product_id": "p2"}
    chain.execute.side_effect = [
        MagicMock(data=[task_a]),
        MagicMock(data=[task_b]),
        MagicMock(data=[]),
        MagicMock(data=[]),
    ]
    out = build_product_compare(
        sb,
        platform_a="a",
        product_id_a="p1",
        platform_b="b",
        product_id_b="p2",
    )
    assert out["_missing"] is True
    assert out["reasons"]["a"] == "empty_analysis"
    assert out["reasons"]["b"] == "empty_analysis"


def test_compare_success_sequence() -> None:
    """按 service 查询顺序提供 8 次 execute 结果。"""
    sb = MagicMock()
    chain = MagicMock()
    sb.table.return_value = chain
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain

    task_a = {"id": "t1", "platform": "a", "product_id": "p1"}
    task_b = {"id": "t2", "platform": "b", "product_id": "p2"}
    chain.execute.side_effect = [
        MagicMock(data=[task_a]),
        MagicMock(data=[task_b]),
        MagicMock(data=[{"sentiment_label": "positive"}, {"sentiment_label": "neutral"}]),
        MagicMock(data=[{"sentiment_label": "positive"}]),
        MagicMock(data=[{"dimension": "cons"}, {"dimension": "pros"}]),
        MagicMock(data=[{"dimension": "cons"}]),
        MagicMock(data=[{"keywords": ["slow"]}, {"keywords": ["fast"]}]),
        MagicMock(data=[{"keywords": ["slow"]}]),
    ]

    out = build_product_compare(
        sb,
        platform_a="a",
        product_id_a="p1",
        platform_b="b",
        product_id_b="p2",
    )
    assert "_missing" not in out or out.get("_missing") is not True
    assert out["product_a"]["insight_task_id"] == "t1"
    assert out["sentiment"]["a"]["positive"] == 1
    assert out["sentiment"]["b"]["positive"] == 1
    assert out["dimensions"]["a"]["cons"] == 1
    assert len(out["conclusion_cards"]) >= 1


def test_delta_map() -> None:
    a = {"negative": 1, "neutral": 0, "positive": 3}
    b = {"negative": 2, "neutral": 1, "positive": 1}
    d = _delta_map(a, b, ("negative", "neutral", "positive"))
    assert d == {"negative": -1, "neutral": -1, "positive": 2}


def test_conclusion_cards_keyword_distinct() -> None:
    ka = Counter({"apple": 5, "banana": 1})
    kb = Counter({"cherry": 4})
    cards = _conclusion_cards(
        {"negative": 0, "neutral": 1, "positive": 9},
        {"negative": 0, "neutral": 1, "positive": 9},
        {k: 0 for k in ("pros", "cons", "return_reasons", "purchase_motivation", "user_expectation", "usage_scenario")},
        {k: 0 for k in ("pros", "cons", "return_reasons", "purchase_motivation", "user_expectation", "usage_scenario")},
        ka,
        kb,
    )
    kinds = {c["kind"] for c in cards}
    assert "keyword" in kinds
