"""TB-8：重试接口（Supabase mock）"""

from unittest.mock import MagicMock, patch
from uuid import UUID

from fastapi.testclient import TestClient

from app.main import app

TID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


def _client() -> TestClient:
    return TestClient(app)


def test_retry_success_task_returns_409() -> None:
    sb = MagicMock()
    exec_ok = MagicMock(
        data=[
            {
                "id": TID,
                "status": "success",
                "platform": "p",
                "product_id": "x",
                "analysis_provider_id": None,
                "error_code": None,
                "error_message": None,
                "failure_stage": None,
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
            }
        ]
    )
    chain = MagicMock()
    sb.table.return_value = chain
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.limit.return_value = chain
    chain.execute.return_value = exec_ok

    with patch("app.modules.tasks.router.require_supabase", return_value=sb):
        r = _client().post(f"/api/v1/insight-tasks/{TID}/retry")
    assert r.status_code == 409


def test_retry_failed_resets_to_pending() -> None:
    sb = MagicMock()
    chain = MagicMock()
    sb.table.return_value = chain
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.limit.return_value = chain
    chain.update.return_value = chain
    chain.select.return_value = chain

    failed_row = {
        "id": TID,
        "status": "failed",
        "platform": "p",
        "product_id": "x",
        "analysis_provider_id": None,
        "error_code": "E",
        "error_message": "m",
        "failure_stage": "fetch",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
    }
    pending_row = {**failed_row, "status": "pending", "error_code": None, "error_message": None, "failure_stage": None}

    chain.execute.side_effect = [
        MagicMock(data=[failed_row]),
        MagicMock(data=[pending_row]),
    ]

    with patch("app.modules.tasks.router.require_supabase", return_value=sb):
        r = _client().post(f"/api/v1/insight-tasks/{TID}/retry")
    assert r.status_code == 200
    body = r.json()
    assert body["action"] == "reset_to_pending"
    assert body["task"]["status"] == "pending"
