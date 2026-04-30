"""词典审核通过写入 overlay：RBAC 与基本校验。"""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.integrations.supabase import require_supabase
from app.main import app


def _client() -> TestClient:
    return TestClient(app)


def _with_mock_supabase() -> None:
    app.dependency_overrides[require_supabase] = lambda: MagicMock()


def _clear_overrides() -> None:
    app.dependency_overrides.pop(require_supabase, None)


def test_dictionary_review_queue_ok_readonly() -> None:
    sb = MagicMock()
    chain = MagicMock()
    sb.table.return_value = chain
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.order.return_value = chain
    chain.execute.return_value = MagicMock(data=[])
    app.dependency_overrides[require_supabase] = lambda: sb
    try:
        r = _client().get(
            "/api/v1/dictionary/review-queue",
            headers={"X-RSA-Role": "readonly"},
        )
        assert r.status_code == 200
        assert r.json() == {"items": []}
    finally:
        _clear_overrides()


def test_dictionary_review_queue_maps_row() -> None:
    sb = MagicMock()
    chain = MagicMock()
    sb.table.return_value = chain
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.order.return_value = chain
    chain.execute.return_value = MagicMock(
        data=[
            {
                "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "kind": "new_discovery",
                "canonical": "battery life",
                "synonyms": ["battery dies fast"],
                "dictionary_vertical_id": "general",
                "dimension_6way": "cons",
                "batch_id": "b1",
                "source_topic_id": "t1",
                "quality_score": 0.9,
                "status": "pending",
            }
        ],
    )
    app.dependency_overrides[require_supabase] = lambda: sb
    try:
        r = _client().get(
            "/api/v1/dictionary/review-queue",
            headers={"X-RSA-Role": "readonly"},
        )
        assert r.status_code == 200
        body = r.json()
        assert len(body["items"]) == 1
        it = body["items"][0]
        assert it["id"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        assert it["kind"] == "new_discovery"
        assert it["canonical"] == "battery life"
        assert it["synonyms"] == ["battery dies fast"]
        assert it["vertical_id"] == "general"
        assert it["dimension_6way"] == "cons"
    finally:
        _clear_overrides()


def test_readonly_dictionary_approve_entry_forbidden() -> None:
    r = _client().post(
        "/api/v1/dictionary/approve-entry",
        json={
            "vertical_ids": ["general"],
            "dimension_6way": "cons",
            "canonical": "test term",
            "aliases": ["alias one"],
        },
        headers={"X-RSA-Role": "readonly"},
    )
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "RBAC_FORBIDDEN"


def test_dictionary_approve_invalid_dimension() -> None:
    _with_mock_supabase()
    try:
        r = _client().post(
            "/api/v1/dictionary/approve-entry",
            json={
                "vertical_ids": ["general"],
                "dimension_6way": "not_a_dim",
                "canonical": "test term",
                "aliases": [],
            },
            headers={"X-RSA-Role": "admin"},
        )
        assert r.status_code == 400
    finally:
        _clear_overrides()


def test_dictionary_approve_entry_ok_writes_db() -> None:
    _with_mock_supabase()
    fake_write = {
        "vertical_id": "electronics",
        "path": "supabase://taxonomy_entries",
        "version": "db",
        "entry_count": 2,
    }
    try:
        with patch(
            "app.modules.dictionary.router.merge_entry_into_vertical_overlay",
            return_value=fake_write,
        ) as m:
            r = _client().post(
                "/api/v1/dictionary/approve-entry",
                json={
                    "vertical_ids": ["electronics"],
                    "dimension_6way": "cons",
                    "canonical": "test term",
                    "aliases": ["a1"],
                },
                headers={"X-RSA-Role": "admin"},
            )
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        assert body["updated"] == [fake_write]
        m.assert_called_once()
    finally:
        _clear_overrides()


def test_dictionary_review_queue_post_manual_forbidden_readonly() -> None:
    r = _client().post(
        "/api/v1/dictionary/review-queue",
        json={"canonical": "keyword", "synonyms": ["alias one"]},
        headers={"X-RSA-Role": "readonly"},
    )
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "RBAC_FORBIDDEN"


def test_dictionary_review_queue_post_manual_ok_insert() -> None:
    sb = MagicMock()
    queue = MagicMock()
    sb.table.return_value = queue
    queue.select.return_value = queue
    queue.eq.return_value = queue
    queue.limit.return_value = queue
    queue.insert.return_value = queue
    empty = MagicMock(data=[])
    inserted = MagicMock(
        data=[
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "kind": "new_discovery",
                "canonical": "keyword",
                "synonyms": ["alias one"],
                "dictionary_vertical_id": "electronics",
                "dimension_6way": None,
                "batch_id": "manual:test",
                "source_topic_id": "manual-ui",
                "quality_score": None,
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
                "status": "pending",
            }
        ],
    )
    queue.execute.side_effect = [empty, inserted]
    app.dependency_overrides[require_supabase] = lambda: sb
    try:
        r = _client().post(
            "/api/v1/dictionary/review-queue",
            json={"canonical": "keyword", "synonyms": ["alias one"]},
            headers={"X-RSA-Role": "admin"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        assert body.get("merged") is False
        assert body["item"]["canonical"] == "keyword"
        assert body["item"]["synonyms"] == ["alias one"]
        assert body["item"]["vertical_id"] == "electronics"
    finally:
        _clear_overrides()
