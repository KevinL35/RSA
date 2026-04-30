"""TB-8：洞察看板空态"""

from unittest.mock import MagicMock
from uuid import UUID

from app.modules.insight_dashboard.service import build_insight_dashboard


def test_dashboard_not_found() -> None:
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
        MagicMock(data=[])
    )
    out = build_insight_dashboard(sb, UUID("00000000-0000-4000-8000-000000000001"))
    assert out.get("_not_found") is True


def test_dashboard_task_not_ready() -> None:
    sb = MagicMock()
    chain = MagicMock()
    sb.table.return_value = chain
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.limit.return_value = chain
    chain.execute.side_effect = [
        MagicMock(
            data=[
                {
                    "platform": "amazon",
                    "product_id": "X",
                    "status": "running",
                }
            ]
        ),
        MagicMock(count=12, data=[{"id": "00000000-0000-0000-0000-000000000099"}]),
    ]
    out = build_insight_dashboard(sb, UUID("00000000-0000-4000-8000-000000000002"))
    assert out["empty_state"]["code"] == "TASK_NOT_READY"
    assert out.get("review_timeseries") == []
    assert out.get("review_total_count") == 12
    assert out.get("matched_review_count") == 0
    assert "analysis_provider_id" in out
    assert "analyzed_at" in out
