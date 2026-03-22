"""TB-11：翻译代理未配置时返回 configured=false"""

from fastapi.testclient import TestClient

from app.main import app


def test_translate_not_configured_returns_200() -> None:
    client = TestClient(app)
    res = client.post(
        "/api/v1/translate",
        json={"text": "Hello world", "target": "zh-CN"},
        headers={"X-RSA-Role": "readonly"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data.get("configured") is False
    assert data.get("translated") is None
