from __future__ import annotations


class ReviewProviderError(Exception):
    """业务可映射为 insight_tasks.error_code / error_message。"""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)
