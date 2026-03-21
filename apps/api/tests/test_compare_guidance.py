"""TB-10：对比前置错误文案"""

from app.modules.compare.guidance import format_compare_prerequisite_error


def test_format_prerequisite_one_side_no_task() -> None:
    raw = {
        "_missing": True,
        "reasons": {"a": "no_success_task", "b": None},
        "products": {
            "a": {"platform": "x", "product_id": "1", "insight_task_id": None},
            "b": {"platform": "y", "product_id": "2", "insight_task_id": "tid"},
        },
    }
    d = format_compare_prerequisite_error(raw)
    assert d["code"] == "MISSING_INSIGHT_DATA"
    assert d["missing"] == {"a": True, "b": False}
    assert "洞察分析" in d["messages"]["zh_CN"]
    assert "Insight analysis" in d["messages"]["en"]
    assert d["next_step"]["route"] == "/insight-analysis"
    assert "guidance" in d


def test_format_prerequisite_empty_analysis() -> None:
    raw = {
        "_missing": True,
        "reasons": {"a": "empty_analysis", "b": None},
        "products": {
            "a": {"platform": "x", "product_id": "1", "insight_task_id": "u1"},
            "b": {"platform": "y", "product_id": "2", "insight_task_id": "u2"},
        },
    }
    d = format_compare_prerequisite_error(raw)
    assert "落库" in d["messages"]["zh_CN"]
    assert d["reasons"]["a"] == "empty_analysis"
