"""TB-8：状态机单测"""

from app.modules.tasks.state_machine import assert_valid_transition


def test_failed_to_pending_allowed() -> None:
    assert_valid_transition("failed", "pending")


def test_success_to_pending_still_invalid() -> None:
    try:
        assert_valid_transition("success", "pending")
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_success_to_running_allowed() -> None:
    assert_valid_transition("success", "running")
