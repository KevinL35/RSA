from app.integrations.agent_enrichment.merge import (
    dedupe_keywords,
    is_dictionary_gap,
    merge_gap_fill,
    merge_sample_keywords,
)


def test_is_dictionary_gap_empty() -> None:
    assert is_dictionary_gap({"review_id": "1", "dimensions": []}) is True
    assert is_dictionary_gap({"review_id": "1", "dimensions": None}) is True  # type: ignore[arg-type]


def test_is_dictionary_gap_no_keywords() -> None:
    item = {
        "review_id": "1",
        "dimensions": [{"dimension": "pros", "keywords": [], "evidence_quote": None, "highlight_spans": []}],
    }
    assert is_dictionary_gap(item) is True


def test_is_dictionary_gap_has_keyword() -> None:
    item = {
        "review_id": "1",
        "dimensions": [{"dimension": "pros", "keywords": ["fast"], "evidence_quote": None, "highlight_spans": []}],
    }
    assert is_dictionary_gap(item) is False


def test_merge_gap_fill() -> None:
    base = {"review_id": "a", "sentiment": {"label": "neutral", "confidence": None}, "dimensions": []}
    agent = {
        "review_id": "a",
        "sentiment": {"label": "positive", "confidence": 0.9},
        "dimensions": [
            {"dimension": "pros", "keywords": ["great"], "evidence_quote": "great", "highlight_spans": []}
        ],
    }
    m = merge_gap_fill(base, agent)
    assert m["dimensions"][0]["keywords"] == ["great"]
    assert m["sentiment"]["label"] == "positive"


def test_merge_gap_fill_agent_empty_keeps_base() -> None:
    base = {"review_id": "a", "sentiment": {"label": "neutral", "confidence": None}, "dimensions": []}
    agent = {"review_id": "a", "dimensions": []}
    m = merge_gap_fill(base, agent)
    assert m == base


def test_merge_sample_keywords() -> None:
    base = {
        "review_id": "b",
        "sentiment": {"label": "neutral", "confidence": None},
        "dimensions": [
            {"dimension": "cons", "keywords": ["slow"], "evidence_quote": None, "highlight_spans": []}
        ],
    }
    agent = {
        "review_id": "b",
        "dimensions": [
            {"dimension": "cons", "keywords": ["slow", "hot"], "evidence_quote": "too hot", "highlight_spans": []}
        ],
    }
    m = merge_sample_keywords(base, agent)
    assert set(m["dimensions"][0]["keywords"]) == {"slow", "hot"}
    assert m["dimensions"][0]["evidence_quote"] == "too hot"


def test_dedupe_keywords() -> None:
    assert dedupe_keywords(["A", "a", "b"]) == ["A", "b"]
