from app.core.config import Settings
from app.integrations.analysis_provider.resolve import resolve_analysis_endpoint


def test_deepseek_chat_fallback_url() -> None:
    cfg = Settings(
        analysis_provider_url="",
        analysis_provider_routes_json=None,
        deepseek_adapter_analyze_url="http://127.0.0.1:9100/analyze",
    )
    _eid, url = resolve_analysis_endpoint(cfg, "deepseek_chat")
    assert url == "http://127.0.0.1:9100/analyze"


def test_routes_override_deepseek() -> None:
    cfg = Settings(
        analysis_provider_url="",
        analysis_provider_routes_json='{"deepseek_chat": "http://custom/analyze"}',
        deepseek_adapter_analyze_url="http://127.0.0.1:9100/analyze",
    )
    _eid, url = resolve_analysis_endpoint(cfg, "deepseek_chat")
    assert url == "http://custom/analyze"


def test_deepseek_chat_before_global_analysis_url() -> None:
    """全局 ANALYSIS_PROVIDER_URL 指向 analysis-api 时，deepseek_chat 仍用适配层。"""
    cfg = Settings(
        analysis_provider_url="http://127.0.0.1:8089/analyze",
        analysis_provider_routes_json=None,
        deepseek_adapter_analyze_url="http://127.0.0.1:9100/analyze",
    )
    _eid, url = resolve_analysis_endpoint(cfg, "deepseek_chat")
    assert url == "http://127.0.0.1:9100/analyze"
