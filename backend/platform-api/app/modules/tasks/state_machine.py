"""洞察任务状态迁移规则（TB-1）。"""

from __future__ import annotations

ALLOWED_STATUSES = frozenset(
    {"pending", "running", "success", "failed", "cancelled"}
)

_VALID_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending": frozenset({"running", "cancelled"}),
    "running": frozenset({"success", "failed", "cancelled"}),
    "failed": frozenset({"pending"}),
    "success": frozenset({"running"}),
    "cancelled": frozenset(),
}


def assert_valid_transition(current: str, target: str) -> None:
    if current not in ALLOWED_STATUSES:
        raise ValueError(f"未知当前状态：{current!r}")
    if target not in ALLOWED_STATUSES:
        raise ValueError(f"未知目标状态：{target!r}")
    allowed = _VALID_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise ValueError(f"不允许从 {current!r} 迁移到 {target!r}")


def should_clear_errors(target: str) -> bool:
    """进入成功、取消、重新排队或开始执行时清空错误字段。"""
    return target in {"pending", "running", "success", "cancelled"}


def is_failed_transition_invalid(
    failure_stage: str | None, error_message: str | None
) -> bool:
    """failed 态必须带可展示的失败阶段与错误信息。"""
    if not (failure_stage and failure_stage.strip()):
        return True
    if not (error_message and error_message.strip()):
        return True
    return False
