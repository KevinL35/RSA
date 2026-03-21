"""TB-13/TB-14：RBAC 与越权拒绝"""

from unittest.mock import MagicMock, patch
from uuid import UUID

from fastapi.testclient import TestClient

from app.main import app

TID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")


def _client() -> TestClient:
    return TestClient(app)


def test_missing_role_on_translate_returns_401() -> None:
    r = _client().post("/api/v1/translate", json={"text": "hello", "target": "zh-CN"})
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "MISSING_OR_INVALID_ROLE"


def test_invalid_role_returns_401() -> None:
    r = _client().get(
        "/api/v1/insight-tasks",
        headers={"X-RSA-Role": "superuser"},
    )
    assert r.status_code == 401


def test_readonly_can_get_insight_tasks_list() -> None:
    """只读可 GET 列表（若 Supabase 未配置则 503，但 RBAC 已通过）。"""
    r = _client().get("/api/v1/insight-tasks", headers={"X-RSA-Role": "readonly"})
    assert r.status_code in (200, 503)


def test_readonly_can_post_translate() -> None:
    r = _client().post(
        "/api/v1/translate",
        json={"text": "hello", "target": "zh-CN"},
        headers={"X-RSA-Role": "readonly"},
    )
    assert r.status_code == 200
    assert r.json().get("configured") is False


def test_readonly_post_retry_forbidden_without_db() -> None:
    r = _client().post(
        f"/api/v1/insight-tasks/{TID}/retry",
        headers={"X-RSA-Role": "readonly"},
    )
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "RBAC_FORBIDDEN"


def test_operator_post_retry_reaches_handler() -> None:
    sb = MagicMock()
    chain = MagicMock()
    sb.table.return_value = chain
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.limit.return_value = chain
    chain.execute.return_value = MagicMock(
        data=[
            {
                "id": str(TID),
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
    with patch("app.modules.tasks.router.require_supabase", return_value=sb):
        r = _client().post(
            f"/api/v1/insight-tasks/{TID}/retry",
            headers={"X-RSA-Role": "operator"},
        )
    assert r.status_code == 409


def test_readonly_delete_insight_task_forbidden() -> None:
    r = _client().delete(
        f"/api/v1/insight-tasks/{TID}",
        headers={"X-RSA-Role": "readonly"},
    )
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "RBAC_FORBIDDEN"


def test_operator_delete_insight_task_reaches_handler() -> None:
    sb = MagicMock()
    chain = MagicMock()
    sb.table.return_value = chain
    chain.select.return_value = chain
    chain.delete.return_value = chain
    chain.eq.return_value = chain
    chain.limit.return_value = chain
    chain.execute.side_effect = [
        MagicMock(data=[{"id": str(TID)}]),
        MagicMock(data=[]),
    ]
    with patch("app.modules.tasks.router.require_supabase", return_value=sb):
        r = _client().delete(
            f"/api/v1/insight-tasks/{TID}",
            headers={"X-RSA-Role": "operator"},
        )
    assert r.status_code == 200
    assert r.json().get("ok") is True


def test_admin_post_retry_same_as_operator() -> None:
    sb = MagicMock()
    chain = MagicMock()
    sb.table.return_value = chain
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.limit.return_value = chain
    chain.execute.return_value = MagicMock(
        data=[
            {
                "id": str(TID),
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
    with patch("app.modules.tasks.router.require_supabase", return_value=sb):
        r = _client().post(
            f"/api/v1/insight-tasks/{TID}/retry",
            headers={"X-RSA-Role": "admin"},
        )
    assert r.status_code == 409
