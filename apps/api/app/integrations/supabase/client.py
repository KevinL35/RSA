from __future__ import annotations

from supabase import Client, create_client

from app.core.config import get_settings

from .postgrest_execute_retry import install_postgrest_execute_retry

_client: Client | None = None


def get_supabase() -> Client | None:
    """Return Supabase client when URL + service role key are configured."""
    global _client
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return None
    if _client is None:
        install_postgrest_execute_retry()
        _client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key,
        )
    return _client


def require_supabase() -> Client:
    client = get_supabase()
    if client is None:
        raise RuntimeError(
            "Supabase 未配置：请在 apps/api/.env 设置 SUPABASE_URL 与 SUPABASE_SERVICE_ROLE_KEY"
        )
    return client
