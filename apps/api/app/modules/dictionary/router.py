from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from app.core.rbac import get_rsa_role, get_rsa_username_optional, require_mutator_role
from app.integrations.supabase import get_supabase, require_supabase
from app.modules.audit_log.service import audit_actor_name, try_record_audit
from supabase import Client

from .import_dictionary_excel import MAX_DICTIONARY_FILE_BYTES, parse_dictionary_excel_rows
from .overlay_publish import (
    build_dictionary_review_entry,
    merge_entries_bulk_into_vertical_overlay,
    merge_entry_into_vertical_overlay,
)
from .taxonomy_yaml import SIX_WAY_DIMENSION_ORDER, group_by_dimension, load_merged_entries_for_vertical
from .verticals import DICTIONARY_VERTICALS, assert_valid_vertical_id

router = APIRouter(prefix="/api/v1/dictionary", tags=["dictionary"])


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_synonyms_json(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    return []


def _map_queue_row(row: dict) -> dict:
    dim = row.get("dimension_6way")
    return {
        "id": str(row["id"]),
        "kind": row["kind"],
        "canonical": row["canonical"],
        "synonyms": _normalize_synonyms_json(row.get("synonyms")),
        "vertical_id": (row.get("dictionary_vertical_id") or "general").strip() or "general",
        "dimension_6way": dim.strip() if isinstance(dim, str) and dim.strip() else None,
        "batch_id": row.get("batch_id"),
        "source_topic_id": row.get("source_topic_id"),
        "quality_score": row.get("quality_score"),
    }


def _parse_queue_uuid(queue_id: str) -> uuid.UUID:
    try:
        return uuid.UUID((queue_id or "").strip())
    except ValueError as e:
        raise HTTPException(status_code=400, detail="无效队列 id") from e


@router.get("/verticals")
def list_dictionary_verticals(
    _rbac: Annotated[str, Depends(get_rsa_role)],
) -> dict:
    """一级词典垂直列表（类目），供洞察任务与词典管理页选择。"""
    return {
        "items": list(DICTIONARY_VERTICALS),
        "dimension_order": list(SIX_WAY_DIMENSION_ORDER),
    }


@router.get("/review-queue")
def get_dictionary_review_queue(
    _rbac: Annotated[str, Depends(get_rsa_role)],
    sb: Client = Depends(require_supabase),
) -> dict:
    """待审核词条列表：`dictionary_review_queue` 中 status=pending 的行（生产由管线/BERTopic/导入写入）。"""
    try:
        res = (
            sb.table("dictionary_review_queue")
            .select("*")
            .eq("status", "pending")
            .order("created_at", desc=False)
            .execute()
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"读取词典审核队列失败：{e!s}",
        ) from e
    rows = res.data or []
    return {"items": [_map_queue_row(r) for r in rows]}


class PatchReviewQueueBody(BaseModel):
    canonical: str = Field(min_length=2, max_length=512)
    synonyms: list[str] = Field(min_length=1, max_length=80)


@router.patch("/review-queue/{queue_id}")
def patch_dictionary_review_queue(
    queue_id: str,
    body: PatchReviewQueueBody,
    _rbac: Annotated[str, Depends(require_mutator_role)],
    sb: Client = Depends(require_supabase),
) -> dict:
    """更新待审行的规范词与同义词（仅 status=pending）。"""
    qid = str(_parse_queue_uuid(queue_id))
    syns = [str(s).strip() for s in body.synonyms if str(s).strip()]
    if not syns:
        raise HTTPException(status_code=400, detail="synonyms 不能为空")
    now = _utc_now_iso()
    try:
        res = (
            sb.table("dictionary_review_queue")
            .update(
                {
                    "canonical": body.canonical.strip(),
                    "synonyms": syns,
                    "updated_at": now,
                },
            )
            .eq("id", qid)
            .eq("status", "pending")
            .select("*")
            .execute()
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"更新审核队列失败：{e!s}") from e
    data = res.data or []
    if not data:
        raise HTTPException(status_code=404, detail="队列项不存在或已处理")
    return {"ok": True, "item": _map_queue_row(data[0])}


@router.delete("/review-queue/{queue_id}")
def delete_dictionary_review_queue(
    queue_id: str,
    _rbac: Annotated[str, Depends(require_mutator_role)],
    sb: Client = Depends(require_supabase),
) -> dict:
    """删除待审行（如删光同义词后放弃入库）；仅 pending。"""
    qid = str(_parse_queue_uuid(queue_id))
    try:
        res = (
            sb.table("dictionary_review_queue")
            .delete()
            .eq("id", qid)
            .eq("status", "pending")
            .select("*")
            .execute()
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"删除审核队列项失败：{e!s}") from e
    data = res.data or []
    if not data:
        raise HTTPException(status_code=404, detail="队列项不存在或已处理")
    return {"ok": True, "id": qid}


@router.get("/taxonomy-preview")
def get_taxonomy_preview(
    _rbac: Annotated[str, Depends(get_rsa_role)],
    vertical_id: str = Query(..., description="词典垂直 id，如 general / electronics"),
) -> dict:
    """按垂直返回合并后的词条，按六维分组（只读预览，供词典管理 UI）。"""
    try:
        vid = assert_valid_vertical_id(vertical_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    try:
        entries = load_merged_entries_for_vertical(vid, sb=get_supabase())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"读取词典配置失败：{e!s}") from e

    grouped = group_by_dimension(entries)
    return {
        "vertical_id": vid,
        "entry_count": len(entries),
        "dimension_order": list(SIX_WAY_DIMENSION_ORDER),
        "dimensions": {
            dim: {
                "key": dim,
                "count": len(grouped.get(dim, [])),
                "entries": grouped.get(dim, []),
            }
            for dim in SIX_WAY_DIMENSION_ORDER
        },
    }


@router.post("/import-excel")
async def post_dictionary_import_excel(
    _rbac: Annotated[str, Depends(require_mutator_role)],
    vertical_id: str = Form(..., description="词典垂直 id，如 general / electronics"),
    file: UploadFile = File(..., description="词典 Excel（.xlsx）"),
    actor: Annotated[str | None, Depends(get_rsa_username_optional)] = None,
    sb: Client = Depends(require_supabase),
) -> dict:
    """将 Excel 中的词条批量 upsert 进 Supabase 对应垂直的 overlay（表头：六维维度、规范词、同义词、权重、优先级）。"""
    try:
        vid = assert_valid_vertical_id(vertical_id.strip())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    raw_name = (file.filename or "").strip()
    if not raw_name.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="请上传 .xlsx 文件")

    content = await file.read()
    if len(content) > MAX_DICTIONARY_FILE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"文件超过 {MAX_DICTIONARY_FILE_BYTES // (1024 * 1024)}MB",
        )

    rows, parse_errors = parse_dictionary_excel_rows(content, filename=raw_name)
    if not rows:
        msg = "；".join(parse_errors) if parse_errors else "未解析到有效数据行"
        raise HTTPException(status_code=400, detail=msg)

    batch_id = f"excel-import-{uuid.uuid4().hex[:12]}"
    entries: list[dict[str, Any]] = []
    row_errors: list[str] = list(parse_errors)
    for r in rows:
        try:
            entries.append(
                build_dictionary_review_entry(
                    dimension_6way=r["dimension_6way"],
                    canonical=r["canonical"],
                    aliases=r["aliases"],
                    actor_username=audit_actor_name(actor),
                    batch_id=batch_id,
                    source_topic_id=None,
                    weight=r["weight"],
                    priority=r["priority"],
                    entry_source="dictionary_excel",
                ),
            )
        except ValueError as e:
            row_errors.append(f"第 {r.get('_row', '?')} 行：{e!s}")

    if not entries:
        raise HTTPException(
            status_code=400,
            detail="；".join(row_errors[:30]) or "无有效词条",
        )

    try:
        updated = merge_entries_bulk_into_vertical_overlay(sb, vid, entries)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"写入词典表 taxonomy_entries 失败：{e!s}",
        ) from e

    try_record_audit(
        sb,
        username=audit_actor_name(actor),
        menu_key="dictionary",
        message=f"词典 Excel 导入：{vid}，{len(entries)} 条",
        detail={
            "vertical_id": vid,
            "imported": len(entries),
            "batch_id": batch_id,
            "filename": raw_name,
            "overlay": updated,
            "warnings": row_errors[:100],
        },
    )
    return {
        "ok": True,
        "imported": len(entries),
        "warnings": row_errors[:50] if row_errors else [],
        "updated": updated,
        "hint": "若使用独立分析服务加载词典，请 POST /admin/reload-taxonomy 或重启该服务。",
    }


class ApproveDictionaryEntryBody(BaseModel):
    """词典审核通过：写入各选中类目的 Supabase overlay（taxonomy_entries）。"""

    vertical_ids: list[str] = Field(min_length=1, max_length=16)
    dimension_6way: str = Field(min_length=1, max_length=64)
    canonical: str = Field(min_length=2, max_length=512)
    aliases: list[str] = Field(default_factory=list, max_length=80)
    batch_id: str | None = Field(default=None, max_length=128)
    source_topic_id: str | None = Field(default=None, max_length=128)
    review_queue_id: str | None = Field(
        default=None,
        max_length=64,
        description="对应 dictionary_review_queue.id，通过后标记为 approved",
    )


@router.post("/approve-entry")
def post_approve_dictionary_entry(
    body: ApproveDictionaryEntryBody,
    _rbac: Annotated[str, Depends(require_mutator_role)],
    actor: Annotated[str | None, Depends(get_rsa_username_optional)] = None,
    sb: Client = Depends(require_supabase),
) -> dict:
    """词典审核通过：合并进 Supabase taxonomy_entries（overlay）；taxonomy-preview 可立即读到。"""
    dim = body.dimension_6way.strip().lower()
    if dim not in SIX_WAY_DIMENSION_ORDER:
        raise HTTPException(
            status_code=400,
            detail=f"无效 dimension_6way：{body.dimension_6way!r}",
        )
    seen: set[str] = set()
    vertical_ids: list[str] = []
    for raw in body.vertical_ids:
        vid = raw.strip()
        if not vid or vid in seen:
            continue
        try:
            assert_valid_vertical_id(vid)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        seen.add(vid)
        vertical_ids.append(vid)
    if not vertical_ids:
        raise HTTPException(status_code=400, detail="vertical_ids 不能为空")

    rq = (body.review_queue_id or "").strip()
    if rq:
        try:
            uuid.UUID(rq)
        except ValueError as e:
            raise HTTPException(status_code=400, detail="无效 review_queue_id") from e

    def _strip_opt(s: str | None) -> str | None:
        if s is None:
            return None
        t = s.strip()
        return t or None

    try:
        entry = build_dictionary_review_entry(
            dimension_6way=dim,
            canonical=body.canonical.strip(),
            aliases=body.aliases,
            actor_username=audit_actor_name(actor),
            batch_id=_strip_opt(body.batch_id),
            source_topic_id=_strip_opt(body.source_topic_id),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    updated: list[dict] = []
    try:
        for vid in vertical_ids:
            updated.append(merge_entry_into_vertical_overlay(sb, vid, dict(entry)))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"写入词典表 taxonomy_entries 失败：{e!s}",
        ) from e

    try_record_audit(
        sb,
        username=audit_actor_name(actor),
        menu_key="pain-audit",
        message=f"词典审核通过：{body.canonical.strip()} → {','.join(vertical_ids)} / {dim}",
        detail={
            "vertical_ids": vertical_ids,
            "dimension_6way": dim,
            "canonical": body.canonical.strip(),
            "aliases": entry.get("aliases"),
            "overlay_writes": updated,
            "review_queue_id": rq or None,
        },
    )
    if rq:
        now = _utc_now_iso()
        try:
            sb.table("dictionary_review_queue").update({"status": "approved", "updated_at": now}).eq(
                "id", rq
            ).eq("status", "pending").execute()
        except Exception:  # noqa: BLE001
            pass
    return {
        "ok": True,
        "vertical_ids": vertical_ids,
        "dimension_6way": dim,
        "canonical": body.canonical.strip(),
        "updated": updated,
        "hint": "若使用独立分析服务加载词典，请 POST /admin/reload-taxonomy 或重启该服务。",
    }


class RejectSynonymBody(BaseModel):
    vertical_id: str = Field(min_length=1, max_length=64)
    dimension_6way: str = Field(min_length=1, max_length=64)
    canonical: str = Field(min_length=1, max_length=512)
    alias: str = Field(min_length=1, max_length=512)


@router.post("/reject-synonym")
def post_reject_synonym(
    body: RejectSynonymBody,
    _rbac: Annotated[str, Depends(require_mutator_role)],
    actor: Annotated[str | None, Depends(get_rsa_username_optional)] = None,
    sb: Client = Depends(require_supabase),
) -> dict:
    """记录「同义词与关键词不匹配」的驳回意向，后续接入词典审核队列与词典版本。"""
    try:
        assert_valid_vertical_id(body.vertical_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    dim = body.dimension_6way.strip().lower()
    if dim not in SIX_WAY_DIMENSION_ORDER:
        raise HTTPException(
            status_code=400,
            detail=f"无效 dimension_6way：{body.dimension_6way!r}",
        )
    try_record_audit(
        sb,
        username=audit_actor_name(actor),
        menu_key="dictionary",
        message=f"驳回同义词：{body.canonical.strip()} ↔ {body.alias.strip()}",
        detail={
            "vertical_id": body.vertical_id.strip(),
            "dimension_6way": dim,
            "canonical": body.canonical.strip(),
            "alias": body.alias.strip(),
        },
    )
    return {
        "ok": True,
        "queued": True,
        "vertical_id": body.vertical_id.strip(),
        "dimension_6way": dim,
        "canonical": body.canonical.strip(),
        "alias": body.alias.strip(),
    }
