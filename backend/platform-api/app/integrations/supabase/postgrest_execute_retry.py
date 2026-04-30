"""
对 postgrest 同步 .execute() 做有限次重试，缓解底层 httpx/socket 的瞬态错误
（如 macOS 上 errno 35 EAGAIN / “Resource temporarily unavailable”）。
在首次创建 Supabase client 前安装一次即可作用于全局。
"""

from __future__ import annotations

import errno
import random
import ssl
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

_installed = False


def _is_transient_network_error(exc: BaseException) -> bool:
    if isinstance(exc, ssl.SSLError):
        msg = str(exc).lower()
        if "handshake operation timed out" in msg or "unexpected_eof_while_reading" in msg:
            return True
    if isinstance(exc, OSError):
        en = getattr(exc, "errno", None)
        if en is not None and en in (errno.EAGAIN, errno.EWOULDBLOCK):
            return True
        msg = str(exc).lower()
        if "resource temporarily unavailable" in msg:
            return True
        if "handshake operation timed out" in msg or "eof occurred in violation of protocol" in msg:
            return True
    try:
        import httpx
    except ImportError:
        httpx = None  # type: ignore[assignment]
    if httpx is not None and isinstance(
        exc,
        (
            httpx.ConnectError,
            httpx.ReadTimeout,
            httpx.WriteTimeout,
            httpx.PoolTimeout,
            httpx.RemoteProtocolError,
        ),
    ):
        return True
    cause = getattr(exc, "__cause__", None)
    if cause is not None and cause is not exc:
        return _is_transient_network_error(cause)
    return False


def _retry_call(fn: Callable[[], T], *, attempts: int = 4, base: float = 0.12) -> T:
    last: BaseException | None = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:
            last = e
            if i < attempts - 1 and _is_transient_network_error(e):
                time.sleep(base * (2**i) + random.uniform(0, 0.06))
                continue
            raise
    assert last is not None
    raise last


def install_postgrest_execute_retry() -> None:
    """幂等：为 postgrest 同步各 RequestBuilder.execute 包一层重试。"""
    global _installed
    if _installed:
        return
    from postgrest._sync.request_builder import (
        SyncExplainRequestBuilder,
        SyncMaybeSingleRequestBuilder,
        SyncQueryRequestBuilder,
        SyncSingleRequestBuilder,
    )

    def _wrap(orig: Callable[..., T]) -> Callable[..., T]:
        def execute(self: object) -> T:
            return _retry_call(lambda: orig(self))

        return execute

    for cls in (
        SyncQueryRequestBuilder,
        SyncMaybeSingleRequestBuilder,
        SyncSingleRequestBuilder,
        SyncExplainRequestBuilder,
    ):
        cls.execute = _wrap(cls.execute)  # type: ignore[method-assign]

    _installed = True
