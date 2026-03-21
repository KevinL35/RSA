"""TB-8：任务列表 error 块"""

from app.modules.tasks.listing import enrich_task_for_task_center


def test_enrich_failed_task_has_error_block() -> None:
    row = {
        "id": "1",
        "status": "failed",
        "failure_stage": "fetch",
        "error_code": "E1",
        "error_message": "boom",
    }
    out = enrich_task_for_task_center(row)
    assert out["error"] == {"stage": "fetch", "code": "E1", "message": "boom"}


def test_enrich_success_task_error_null() -> None:
    row = {"id": "1", "status": "success"}
    out = enrich_task_for_task_center(row)
    assert out["error"] is None
