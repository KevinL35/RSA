from __future__ import annotations

import uuid
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from supabase import Client

from app.core.rbac import get_rsa_role, get_rsa_username_optional, require_mutator_role
from app.core.config import get_settings
from app.integrations.supabase import get_supabase, require_supabase
from app.modules.audit_log.service import audit_actor_name, try_record_audit

from .helpers import (
    _adapter_auth_headers,
    _audit_detail,
    _dedupe_synonyms_for_queue,
    _enqueue_rejected_alias_for_review,
    _map_queue_row,
    _normalize_synonyms_json,
    _parse_queue_uuid,
    _remove_alias_from_overlay,
    _utc_now_iso,
    _vertical_label_zh,
)
from .import_dictionary_excel import MAX_DICTIONARY_FILE_BYTES, parse_dictionary_excel_rows
from .overlay_publish import build_dictionary_review_entry, merge_entries_bulk_into_vertical_overlay, merge_entry_into_vertical_overlay
from .schemas import ApproveDictionaryEntryBody, DictionaryTaxonomyAgentReviewRequest, PatchReviewQueueBody, RejectSynonymBody
from .taxonomy_yaml import SIX_WAY_DIMENSION_ORDER, group_by_dimension, load_merged_entries_for_vertical
from .verticals import DEFAULT_VERTICAL_ID, DICTIONARY_VERTICALS, assert_valid_vertical_id

router = APIRouter()
_SIX_DIMS = set(SIX_WAY_DIMENSION_ORDER)

@router.post("/taxonomy/agent-review")
def post_dictionary_taxonomy_agent_review(
    body: DictionaryTaxonomyAgentReviewRequest,
    _rbac: Annotated[str, Depends(require_mutator_role)],
    actor: Annotated[str | None, Depends(get_rsa_username_optional)] = None,
    sb: Client = Depends(require_supabase),
) -> dict:
    """词典维度智能审核：把该维度词条交给模型，驳回不合适词条并回流到主题挖掘队列。"""
    settings = get_settings()
    url = (settings.deepseek_adapter_dictionary_smart_merge_url or "").strip()
    if not url:
        raise HTTPException(
            status_code=400,
            detail="未配置 DEEPSEEK_ADAPTER_DICTIONARY_SMART_MERGE_URL（默认 http://127.0.0.1:9100/dictionary-smart-merge）",
        )
    try:
        vid = assert_valid_vertical_id(body.vertical_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    dim = body.dimension_6way.strip().lower()
    if dim not in _SIX_DIMS:
        raise HTTPException(status_code=400, detail="无效 dimension_6way")

    try:
        res = (
            sb.table("taxonomy_entries")
            .select("id,canonical,aliases")
            .eq("source_layer", "overlay")
            .eq("dictionary_vertical_id", vid)
            .eq("dimension_6way", dim)
            .order("updated_at", desc=True)
            .limit(500)
            .execute()
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"读取词典条目失败：{e!s}") from e
    rows = res.data or []
    entries: list[dict[str, Any]] = []
    for r in rows:
        canonical = str(r.get("canonical") or "").strip()
        aliases = _normalize_synonyms_json(r.get("aliases"))
        if not canonical or not aliases:
            continue
        entries.append(
            {
                "id": str(r.get("id") or "").strip(),
                "canonical": canonical,
                "aliases": aliases,
            }
        )
    if not entries:
        return {
            "ok": True,
            "vertical_id": vid,
            "dimension_6way": dim,
            "total": 0,
            "rejected_entries": 0,
            "rejected_aliases": 0,
            "queued": 0,
        }

    payload = {
        "dictionary_vertical_id": vid,
        "dictionary_label_zh": _vertical_label_zh(vid),
        "dimension_6way": dim,
        "items": [
            {
                "queue_id": str(i),
                "canonical": x["canonical"],
                "synonyms": x["aliases"],
            }
            for i, x in enumerate(entries)
        ],
    }
    timeout = min(240.0, max(60.0, float(settings.agent_enrichment_timeout_seconds or 120.0) * 1.5))
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=payload, headers=_adapter_auth_headers(settings))
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"智能审核服务不可达：{e!s}") from e
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"智能审核服务错误 HTTP {resp.status_code}: {resp.text[:1200]}",
        )
    try:
        outer = resp.json()
    except ValueError as e:
        raise HTTPException(status_code=502, detail=f"智能审核响应非 JSON：{e!s}") from e
    plan = outer.get("plan") if isinstance(outer, dict) else None
    if not isinstance(plan, dict):
        raise HTTPException(status_code=502, detail="智能审核响应缺少 plan")
    rejects = plan.get("rejects") or []
    if not isinstance(rejects, list):
        raise HTTPException(status_code=502, detail="智能审核 plan.rejects 非数组")

    rejected_entries = 0
    rejected_aliases = 0
    queued = 0
    now = _utc_now_iso()
    for item in rejects:
        if not isinstance(item, dict):
            continue
        qid = str(item.get("queue_id") or "").strip()
        reason = str(item.get("reason_zh") or "").strip()[:500]
        if not qid.isdigit():
            continue
        idx = int(qid)
        if idx < 0 or idx >= len(entries):
            continue
        e = entries[idx]
        if not e["id"]:
            continue
        try:
            sb.table("taxonomy_entries").delete().eq("id", e["id"]).execute()
        except Exception as ex:  # noqa: BLE001
            raise HTTPException(status_code=502, detail=f"删除词典条目失败：{ex!s}") from ex
        rejected_entries += 1
        aliases = e["aliases"]
        rejected_aliases += len(aliases)
        first_qid: str | None = None
        for al in aliases:
            qr = _enqueue_rejected_alias_for_review(
                sb,
                vertical_id=vid,
                dimension_6way=dim,
                canonical=e["canonical"],
                alias=al,
                actor_username=actor,
            )
            qrid = str(qr.get("id") or "").strip() or None
            if qrid and not first_qid:
                first_qid = qrid
            if qr.get("action") in {"inserted", "merged"}:
                queued += 1
        try_record_audit(
            sb,
            username=audit_actor_name(actor),
            menu_key="smart-mining",
            message=f"词典智能审核驳回：{e['canonical']}",
            detail=_audit_detail(
                event_type="dictionary_taxonomy_agent_reject",
                action="reject",
                entity="taxonomy_entry",
                source="dictionary-taxonomy-agent-review",
                counts={"aliases": len(aliases)},
                extra={
                    "review_queue_id": first_qid,
                    "vertical_id": vid,
                    "dimension_6way": dim,
                    "canonical": e["canonical"],
                    "aliases": aliases,
                    "reason_zh": reason,
                    "agent_provider": "dictionary-taxonomy-agent-review",
                    "updated_at": now,
                },
            ),
        )

    return {
        "ok": True,
        "vertical_id": vid,
        "dimension_6way": dim,
        "total": len(entries),
        "rejected_entries": rejected_entries,
        "rejected_aliases": rejected_aliases,
        "queued": queued,
    }


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
    vertical_id: str = Query(..., description="词典垂直 id，如 electronics / furniture_kitchen / fashion_shoes_bags"),
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

    def _has_aliases(entry: dict[str, Any]) -> bool:
        als = entry.get("aliases")
        if not isinstance(als, list):
            return False
        return any(str(x).strip() for x in als)

    visible_entries = [e for e in entries if _has_aliases(e)]
    grouped = group_by_dimension(visible_entries)
    return {
        "vertical_id": vid,
        "entry_count": len(visible_entries),
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
    vertical_id: str = Form(..., description="词典垂直 id，如 electronics / furniture_kitchen / fashion_shoes_bags"),
    file: UploadFile = File(..., description="词典 Excel（.xlsx）"),
    actor: Annotated[str | None, Depends(get_rsa_username_optional)] = None,
    sb: Client = Depends(require_supabase),
) -> dict:
    """将 Excel 中的词条批量 upsert 进 Supabase 对应垂直的 overlay（表头：六维维度、规范词、同义词；权重与优先级使用默认值）。"""
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
        detail=_audit_detail(
            event_type="dictionary_import_excel",
            action="import",
            entity="taxonomy_entries.overlay",
            source="excel",
            counts={"imported": len(entries), "warnings": len(row_errors)},
            extra={
                "vertical_id": vid,
                "batch_id": batch_id,
                "filename": raw_name,
                "overlay": updated,
                "warnings": row_errors[:100],
            },
        ),
    )
    return {
        "ok": True,
        "imported": len(entries),
        "warnings": row_errors[:50] if row_errors else [],
        "updated": updated,
        "hint": "若使用独立分析服务加载词典，请 POST /admin/reload-taxonomy 或重启该服务。",
    }


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
        menu_key="smart-mining",
        message=f"词典审核通过：{body.canonical.strip()} → {','.join(vertical_ids)} / {dim}",
        detail=_audit_detail(
            event_type="topic_review_approve",
            action="approve",
            entity="dictionary_review_queue",
            source="manual",
            counts={"vertical_ids": len(vertical_ids), "aliases": len(entry.get("aliases") or [])},
            extra={
                "vertical_ids": vertical_ids,
                "dimension_6way": dim,
                "canonical": body.canonical.strip(),
                "aliases": entry.get("aliases"),
                "overlay_writes": updated,
                "batch_id": _strip_opt(body.batch_id),
                "source_topic_id": _strip_opt(body.source_topic_id),
                "review_queue_id": rq or None,
            },
        ),
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


@router.post("/reject-synonym")
def post_reject_synonym(
    body: RejectSynonymBody,
    _rbac: Annotated[str, Depends(require_mutator_role)],
    actor: Annotated[str | None, Depends(get_rsa_username_optional)] = None,
    sb: Client = Depends(require_supabase),
) -> dict:
    """驳回同义词：从 overlay 删该 alias，再把它作为待审条目写入 dictionary_review_queue。"""
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
    canonical = body.canonical.strip()
    alias = body.alias.strip()
    overlay_result = _remove_alias_from_overlay(
        sb,
        vertical_id=body.vertical_id.strip(),
        dimension_6way=dim,
        canonical=canonical,
        alias=alias,
    )
    queue_result = _enqueue_rejected_alias_for_review(
        sb,
        vertical_id=body.vertical_id.strip(),
        dimension_6way=dim,
        canonical=canonical,
        alias=alias,
        actor_username=actor,
    )
    try_record_audit(
        sb,
        username=audit_actor_name(actor),
        menu_key="dictionary",
        message=f"驳回同义词：{canonical} ↔ {alias}",
        detail=_audit_detail(
            event_type="dictionary_reject_synonym",
            action="reject",
            entity="taxonomy_entries.overlay",
            source="manual",
            extra={
                "vertical_id": body.vertical_id.strip(),
                "dimension_6way": dim,
                "canonical": canonical,
                "alias": alias,
                "overlay_matched": overlay_result.get("matched"),
                "overlay_removed": overlay_result.get("removed"),
                "overlay_entry_deleted": overlay_result.get("entry_deleted"),
                "review_queue_id": queue_result.get("id"),
                "review_queue_action": queue_result.get("action"),
            },
        ),
    )
    return {
        "ok": True,
        "queued": True,
        "vertical_id": body.vertical_id.strip(),
        "dimension_6way": dim,
        "canonical": canonical,
        "alias": alias,
        "overlay_matched": overlay_result.get("matched"),
        "overlay_removed": overlay_result.get("removed"),
        "overlay_entry_deleted": overlay_result.get("entry_deleted"),
        "review_queue_id": queue_result.get("id"),
        "review_queue_action": queue_result.get("action"),
        "review_queue_synonyms": queue_result.get("synonyms"),
        "hint": "若使用独立分析服务加载词典，请 POST /admin/reload-taxonomy 或重启该服务。",
    }
