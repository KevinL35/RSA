"""Mock 分析源在未配置 URL 时也应可用。"""

from app.core.config import Settings
from app.integrations.analysis_provider.client import analyze_reviews


def test_analyze_reviews_mock_without_any_url() -> None:
    cfg = Settings(
        analysis_provider_mock=True,
        analysis_provider_url=None,
        analysis_provider_routes_json=None,
        analysis_provider_default_id="default",
    )
    reviews = [{"id": "00000000-0000-0000-0000-000000000001", "raw_text": "nice"}]
    eid, normalized, _raw = analyze_reviews(
        insight_task_id="00000000-0000-0000-0000-000000000099",
        platform="amazon",
        product_id="B0TEST",
        task_analysis_provider_id="ins_builtin",
        reviews=reviews,
        settings=cfg,
    )
    assert eid == "ins_builtin"
    assert len(normalized) == 1
    assert normalized[0].get("review_id") == "00000000-0000-0000-0000-000000000001"
