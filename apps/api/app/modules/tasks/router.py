from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from app.core.rbac import get_rsa_role, get_rsa_username_optional, require_mutator_role
from app.integrations.supabase import require_supabase
from app.modules.insight_dashboard.service import build_insight_dashboard

from . import state_machine
from .analyze_task import run_analyze_for_task
from .fetch_reviews import run_fetch_reviews_for_task
from .import_reviews_excel import run_import_reviews_from_excel
from .listing import enrich_task_for_task_center, list_insight_tasks_filtered
from .retry_task import retry_insight_task
from app.modules.dictionary.verticals import assert_valid_vertical_id

from .schema import InsightTaskCreate, InsightTaskPatch

router = APIRouter(prefix="/api/v1/insight-tasks", tags=["insight-tasks"])


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("")
def list_insight_tasks(
    _rbac: Annotated[str, Depends(get_rsa_role)],
    task_type: str | None = Query(
        default=None,
        description="任务类型，当前仅 insight（可省略）",
    ),
    status: str | None = Query(
        default=None,
        description="逗号分隔：pending,running,success,failed,cancelled",
    ),
    created_after: str | None = Query(
        default=None,
        description="ISO8601，含该时刻之后创建的任务",
    ),
    created_before: str | None = Query(
        default=None,
        description="ISO8601，含该时刻之前创建的任务",
    ),
    limit: int = Query(default=100, ge=1, le=200),
) -> dict:
    """TB-6：任务中心列表，支持类型/状态/时间筛选；失败任务含结构化 error。"""
    try:
        sb = require_supabase()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    try:
        return list_insight_tasks_filtered(
            sb,
            task_type=task_type,
            status_csv=status,
            created_after=created_after,
            created_before=created_before,
            limit=limit,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=502,
            detail=f"Supabase 查询失败：{e!s}",
        ) from e


@router.post("")
def create_insight_task(
    body: InsightTaskCreate,
    _rbac: Annotated[str, Depends(require_mutator_role)],
    created_by: Annotated[str | None, Depends(get_rsa_username_optional)] = None,
) -> dict:
    try:
        sb = require_supabase()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    try:
        dvid = assert_valid_vertical_id(body.dictionary_vertical_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    row: dict[str, object] = {
        "platform": body.platform.strip(),
        "product_id": body.product_id.strip(),
        "status": "pending",
        "analysis_provider_id": body.analysis_provider_id,
        "dictionary_vertical_id": dvid,
    }
    if created_by:
        row["created_by"] = created_by
    try:
        res = sb.table("insight_tasks").insert(row).execute()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=502,
            detail=f"Supabase 写入失败：{e!s}",
        ) from e
    data = res.data
    if not data:
        raise HTTPException(status_code=500, detail="插入成功但未返回数据，请检查 RLS/策略")
    return enrich_task_for_task_center(data[0])


@router.post("/{task_id}/fetch-reviews")
def post_fetch_reviews(
    task_id: UUID,
    _rbac: Annotated[str, Depends(require_mutator_role)],
) -> dict:
    """TB-2：按任务 platform/product_id 调用评论抓取 API 并写入 reviews。"""
    try:
        sb = require_supabase()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    try:
        return run_fetch_reviews_for_task(sb, task_id)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"抓取流程异常：{e!s}",
        ) from e


@router.post("/{task_id}/import-reviews")
async def post_import_reviews(
    task_id: UUID,
    _rbac: Annotated[str, Depends(require_mutator_role)],
    file: UploadFile = File(..., description="评论 Excel（.xlsx / .xls），表头含时间与评论列"),
) -> dict:
    """从 Excel 导入评论（仅时间与正文列），替换该任务已有 reviews；pending→running，与抓取后状态一致以便继续 analyze。"""
    try:
        sb = require_supabase()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in (".xlsx", ".xls"):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx 或 .xls 文件")
    try:
        content = await file.read()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"读取上传文件失败：{e!s}") from e
    try:
        return run_import_reviews_from_excel(
            sb,
            task_id,
            content,
            filename=file.filename or "",
        )
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"导入评论异常：{e!s}",
        ) from e


@router.get("/{task_id}/reviews")
def get_insight_task_reviews(
    task_id: UUID,
    _rbac: Annotated[str, Depends(get_rsa_role)],
    limit: int = Query(default=5000, ge=1, le=20000),
) -> dict:
    """列出任务已落库评论（供前端导出 CSV 等）；只读角色可访问。"""
    try:
        sb = require_supabase()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    try:
        tr = (
            sb.table("insight_tasks")
            .select("id,platform,product_id,status")
            .eq("id", str(task_id))
            .limit(1)
            .execute()
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Supabase 查询失败：{e!s}") from e
    trows = tr.data or []
    if not trows:
        raise HTTPException(status_code=404, detail="任务不存在")
    task_row = trows[0]
    try:
        rv = (
            sb.table("reviews")
            .select(
                "id,external_review_id,raw_text,title,rating,sku,reviewed_at,lang,extra,created_at",
            )
            .eq("insight_task_id", str(task_id))
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Supabase 查询失败：{e!s}") from e
    items = rv.data or []
    for row in items:
        row["platform"] = task_row["platform"]
        row["product_id"] = task_row["product_id"]
    return {
        "insight_task_id": str(task_id),
        "platform": task_row["platform"],
        "product_id": task_row["product_id"],
        "task_status": task_row["status"],
        "count": len(items),
        "items": items,
    }


@router.get("/{task_id}/dashboard")
def get_insight_dashboard(
    task_id: UUID,
    _rbac: Annotated[str, Depends(get_rsa_role)],
    evidence_limit: int = Query(default=50, ge=1, le=200),
    evidence_offset: int = Query(default=0, ge=0),
    evidence_dimension: str | None = Query(
        default=None,
        description="仅返回该维度的证据分页（与 TA-1 六维 key 一致）",
    ),
) -> dict:
    """TB-5：痛点排行、维度聚合、证据列表（分页）；非 success 返回 empty_state。"""
    try:
        sb = require_supabase()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    try:
        payload = build_insight_dashboard(
            sb,
            task_id,
            evidence_limit=evidence_limit,
            evidence_offset=evidence_offset,
            evidence_dimension=evidence_dimension,
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=502,
            detail=f"聚合失败：{e!s}",
        ) from e
    if payload.get("_not_found"):
        raise HTTPException(status_code=404, detail="任务不存在")
    if "_bad_dimension" in payload:
        raise HTTPException(
            status_code=400,
            detail=f"无效 evidence_dimension：{payload['_bad_dimension']!r}",
        )
    payload.pop("_not_found", None)
    payload.pop("_bad_dimension", None)
    return payload


@router.post("/{task_id}/retry")
def post_insight_task_retry(
    task_id: UUID,
    _rbac: Annotated[str, Depends(require_mutator_role)],
) -> dict:
    """TB-6：幂等重试（failed→pending；已为 pending 则 no-op）。"""
    try:
        sb = require_supabase()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    try:
        return retry_insight_task(sb, task_id)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"重试异常：{e!s}",
        ) from e


@router.get("/{task_id}/analysis")
def get_stored_task_analysis(
    task_id: UUID,
    _rbac: Annotated[str, Depends(get_rsa_role)],
) -> dict:
    """TB-4：读取已落库的分析结果（按任务），含原评论正文便于证据反查。"""
    try:
        sb = require_supabase()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    try:
        tr = (
            sb.table("insight_tasks")
            .select("id,platform,product_id,status")
            .eq("id", str(task_id))
            .limit(1)
            .execute()
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Supabase 查询失败：{e!s}") from e
    trows = tr.data or []
    if not trows:
        raise HTTPException(status_code=404, detail="任务不存在")
    task_row = trows[0]

    try:
        ra = (
            sb.table("review_analysis")
            .select("*")
            .eq("insight_task_id", str(task_id))
            .execute()
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Supabase 查询失败：{e!s}") from e

    analysis_rows = ra.data or []
    if not analysis_rows:
        return {
            "insight_task_id": str(task_id),
            "platform": task_row["platform"],
            "product_id": task_row["product_id"],
            "task_status": task_row["status"],
            "items": [],
        }

    rids = list({str(r["review_id"]) for r in analysis_rows})
    try:
        rv = (
            sb.table("reviews")
            .select("id,raw_text,title,rating,sku,reviewed_at")
            .in_("id", rids)
            .execute()
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Supabase 查询评论失败：{e!s}") from e
    rmap = {str(x["id"]): x for x in (rv.data or [])}

    try:
        dim_res = (
            sb.table("review_dimension_analysis")
            .select("*")
            .eq("insight_task_id", str(task_id))
            .execute()
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Supabase 查询维度失败：{e!s}") from e

    by_ra: dict[str, list] = {}
    for d in dim_res.data or []:
        by_ra.setdefault(str(d["review_analysis_id"]), []).append(d)

    items: list[dict] = []
    for r in analysis_rows:
        ra_id = str(r["id"])
        rid = str(r["review_id"])
        dim_list = by_ra.get(ra_id, [])
        items.append(
            {
                "review_id": rid,
                "review": rmap.get(rid),
                "sentiment": {
                    "label": r["sentiment_label"],
                    "confidence": r.get("sentiment_confidence"),
                },
                "dimensions": [
                    {
                        "dimension": x["dimension"],
                        "keywords": x.get("keywords") or [],
                        "evidence_quote": x.get("evidence_quote"),
                        "highlight_spans": x.get("highlight_spans") or [],
                    }
                    for x in dim_list
                ],
                "analysis_provider_id": r.get("analysis_provider_id"),
                "created_at": r.get("created_at"),
            }
        )

    return {
        "insight_task_id": str(task_id),
        "platform": task_row["platform"],
        "product_id": task_row["product_id"],
        "task_status": task_row["status"],
        "items": items,
    }


@router.post("/{task_id}/analyze")
def post_analyze_insight_task(
    task_id: UUID,
    _rbac: Annotated[str, Depends(require_mutator_role)],
) -> dict:
    """TB-3：对已抓取评论调用分析源，返回情感/六维/证据结构；成功将任务标为 success。"""
    try:
        sb = require_supabase()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    try:
        return run_analyze_for_task(sb, task_id)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"分析流程异常：{e!s}",
        ) from e


@router.get("/{task_id}")
def get_insight_task(
    task_id: UUID,
    _rbac: Annotated[str, Depends(get_rsa_role)],
) -> dict:
    try:
        sb = require_supabase()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    try:
        res = (
            sb.table("insight_tasks")
            .select("*")
            .eq("id", str(task_id))
            .limit(1)
            .execute()
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=502,
            detail=f"Supabase 查询失败：{e!s}",
        ) from e
    rows = res.data or []
    if not rows:
        raise HTTPException(status_code=404, detail="任务不存在")
    return enrich_task_for_task_center(rows[0])


@router.patch("/{task_id}")
def patch_insight_task(
    task_id: UUID,
    body: InsightTaskPatch,
    _rbac: Annotated[str, Depends(require_mutator_role)],
) -> dict:
    try:
        sb = require_supabase()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    try:
        cur = (
            sb.table("insight_tasks")
            .select("status")
            .eq("id", str(task_id))
            .limit(1)
            .execute()
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=502,
            detail=f"Supabase 查询失败：{e!s}",
        ) from e
    rows = cur.data or []
    if not rows:
        raise HTTPException(status_code=404, detail="任务不存在")
    current_status = rows[0]["status"]
    try:
        state_machine.assert_valid_transition(current_status, body.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if body.status == "failed":
        if state_machine.is_failed_transition_invalid(
            body.failure_stage, body.error_message
        ):
            raise HTTPException(
                status_code=400,
                detail="迁移到 failed 时必须提供非空的 failure_stage 与 error_message",
            )

    update: dict = {"status": body.status, "updated_at": _utc_now_iso()}
    if state_machine.should_clear_errors(body.status):
        update["error_code"] = None
        update["error_message"] = None
        update["failure_stage"] = None
    elif body.status == "failed":
        update["error_code"] = body.error_code
        update["error_message"] = body.error_message.strip() if body.error_message else None
        update["failure_stage"] = body.failure_stage.strip() if body.failure_stage else None

    try:
        res = (
            sb.table("insight_tasks")
            .update(update)
            .eq("id", str(task_id))
            .execute()
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=502,
            detail=f"Supabase 更新失败：{e!s}",
        ) from e
    data = res.data
    if not data:
        raise HTTPException(status_code=500, detail="更新成功但未返回数据，请检查 RLS/策略")
    return enrich_task_for_task_center(data[0])


@router.delete("/{task_id}")
def delete_insight_task(
    task_id: UUID,
    _rbac: Annotated[str, Depends(require_mutator_role)],
) -> dict:
    """删除任务；关联 reviews / review_analysis / review_dimension_analysis 由库级 ON DELETE CASCADE 清理。"""
    try:
        sb = require_supabase()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    try:
        cur = (
            sb.table("insight_tasks")
            .select("id")
            .eq("id", str(task_id))
            .limit(1)
            .execute()
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=502,
            detail=f"Supabase 查询失败：{e!s}",
        ) from e
    if not (cur.data or []):
        raise HTTPException(status_code=404, detail="任务不存在")
    try:
        sb.table("insight_tasks").delete().eq("id", str(task_id)).execute()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=502,
            detail=f"Supabase 删除失败：{e!s}",
        ) from e
    return {"ok": True, "id": str(task_id)}
