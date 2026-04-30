from __future__ import annotations

import uuid
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from supabase import Client

from app.core.config import get_settings
from app.core.rbac import get_rsa_role, get_rsa_username_optional, require_mutator_role
from app.integrations.agent_enrichment.client import AgentEnrichmentError, call_agent_enrichment_batch
from app.integrations.supabase import require_supabase
from app.modules.audit_log.service import audit_actor_name, try_record_audit

from .helpers import (
    _adapter_auth_headers,
    _audit_detail,
    _dedupe_synonyms_for_queue,
    _map_queue_row,
    _normalize_synonyms_json,
    _parse_queue_uuid,
    _pick_agent_dimension,
    _utc_now_iso,
    _validate_smart_merge_plan,
    _vertical_label_zh,
)
from .schemas import CreateDictionaryReviewQueueBody, DictionarySmartMergeRequest
from .taxonomy_yaml import SIX_WAY_DIMENSION_ORDER, load_merged_entries_for_vertical
from .verticals import DEFAULT_VERTICAL_ID, DICTIONARY_VERTICALS, assert_valid_vertical_id

router = APIRouter()
_SIX_DIMS = set(SIX_WAY_DIMENSION_ORDER)

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


@router.post("/review-queue")
def post_dictionary_review_queue(
    body: CreateDictionaryReviewQueueBody,
    _rbac: Annotated[str, Depends(require_mutator_role)],
    sb: Client = Depends(require_supabase),
) -> dict:
    keyword = body.canonical.strip()
    if len(keyword) < 2:
        raise HTTPException(status_code=400, detail="canonical 过短")
    raw_vid = (body.vertical_id or "").strip() or DEFAULT_VERTICAL_ID
    try:
        assert_valid_vertical_id(raw_vid)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    vid = raw_vid

    syns = _dedupe_synonyms_for_queue([str(s) for s in body.synonyms], exclude_canonical=keyword)
    if not syns:
        raise HTTPException(
            status_code=400,
            detail="synonyms 至少保留一条有效同义词（且不能与关键词相同）",
        )

    now = _utc_now_iso()
    batch_id = f"manual:{uuid.uuid4()}"

    try:
        existed = (
            sb.table("dictionary_review_queue")
            .select("id, synonyms, kind")
            .eq("status", "pending")
            .eq("dictionary_vertical_id", vid)
            .eq("canonical", keyword)
            .limit(1)
            .execute()
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=502,
            detail=f"查询 dictionary_review_queue 失败：{e!s}",
        ) from e

    existed_rows = existed.data or []
    if existed_rows:
        cur = existed_rows[0]
        cur_syn = _normalize_synonyms_json(cur.get("synonyms"))
        merged = _dedupe_synonyms_for_queue([*cur_syn, *syns], exclude_canonical=keyword)
        if not merged:
            raise HTTPException(status_code=400, detail="合并后同义词为空")
        try:
            res = (
                sb.table("dictionary_review_queue")
                .update(
                    {
                        "synonyms": merged,
                        "canonical": keyword,
                        "updated_at": now,
                    },
                )
                .eq("id", cur["id"])
                .eq("status", "pending")
                .execute()
            )
        except Exception as e:  # noqa: BLE001
            raise HTTPException(
                status_code=502,
                detail=f"合并 dictionary_review_queue 失败：{e!s}",
            ) from e
        data = res.data or []
        if not data:
            raise HTTPException(status_code=404, detail="队列项不存在或已处理")
        return {"ok": True, "merged": True, "item": _map_queue_row(data[0])}

    payload: dict[str, Any] = {
        "kind": "new_discovery",
        "canonical": keyword,
        "synonyms": syns,
        "dictionary_vertical_id": vid,
        "dimension_6way": None,
        "batch_id": batch_id,
        "source_topic_id": "manual-ui",
        "status": "pending",
    }
    try:
        ins = sb.table("dictionary_review_queue").insert(payload).execute()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=502,
            detail=f"写入 dictionary_review_queue 失败：{e!s}",
        ) from e
    rows_ins = ins.data or []
    if not rows_ins:
        raise HTTPException(status_code=502, detail="写入审核队列为空响应")
    return {"ok": True, "merged": False, "item": _map_queue_row(rows_ins[0])}


@router.get("/review-records")
def get_dictionary_review_records(
    _rbac: Annotated[str, Depends(get_rsa_role)],
    limit: int = Query(default=100, ge=1, le=500),
    sb: Client = Depends(require_supabase),
) -> dict:
    """审核记录：聚合智能体审核与人工通过记录，返回可追踪链路。"""
    try:
        res = (
            sb.table("audit_logs")
            .select("id,message,detail,created_at")
            .eq("menu_key", "smart-mining")
            .order("created_at", desc=True)
            .limit(max(200, min(2000, limit * 10)))
            .execute()
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"读取审核记录失败：{e!s}",
        ) from e
    rows = res.data or []
    records: dict[str, dict[str, Any]] = {}

    for row in rows:
        detail = row.get("detail") or {}
        if not isinstance(detail, dict):
            continue
        rqid = str(detail.get("review_queue_id") or "").strip()
        canonical = str(detail.get("canonical") or "").strip()
        if not rqid and not canonical:
            continue
        key = rqid or f"canonical:{canonical.lower()}"
        item = records.get(key) or {
            "review_queue_id": rqid or None,
            "canonical": canonical or None,
            "synonyms": [],
            "agent_reviewed_at": None,
            "suggested_dimension_6way": None,
            "approved_at": None,
            "approved_dimension_6way": None,
            "vertical_ids": [],
            "target_dictionary_table": None,
        }

        if "suggested_dimension_6way" in detail:
            item["agent_reviewed_at"] = row.get("created_at")
            item["suggested_dimension_6way"] = detail.get("suggested_dimension_6way")
            syns = detail.get("synonyms")
            if isinstance(syns, list):
                item["synonyms"] = [str(x).strip() for x in syns if str(x).strip()]

        if "vertical_ids" in detail and "dimension_6way" in detail:
            item["approved_at"] = row.get("created_at")
            item["approved_dimension_6way"] = detail.get("dimension_6way")
            vids = detail.get("vertical_ids")
            if isinstance(vids, list):
                item["vertical_ids"] = [str(x).strip() for x in vids if str(x).strip()]
            aliases = detail.get("aliases")
            if isinstance(aliases, list):
                item["synonyms"] = [str(x).strip() for x in aliases if str(x).strip()]
            item["target_dictionary_table"] = "taxonomy_entries.overlay"
            if canonical:
                item["canonical"] = canonical

        records[key] = item

    out = [v for v in records.values() if v.get("approved_at") or v.get("agent_reviewed_at")]
    out.sort(key=lambda x: str(x.get("approved_at") or x.get("agent_reviewed_at") or ""), reverse=True)
    return {"items": out[:limit], "limit": limit}


@router.get("/review-merge-logs")
def get_dictionary_review_merge_logs(
    _rbac: Annotated[str, Depends(get_rsa_role)],
    limit: int = Query(default=100, ge=1, le=500),
    sb: Client = Depends(require_supabase),
) -> dict:
    """合并结果日志：展示通过/驳回结果与来源（source_topic_id / batch_id）。"""
    try:
        res = (
            sb.table("audit_logs")
            .select("id,detail,created_at")
            .eq("menu_key", "smart-mining")
            .order("created_at", desc=True)
            .limit(max(300, min(3000, limit * 15)))
            .execute()
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"读取合并日志失败：{e!s}") from e

    rows = res.data or []
    queue_ids: list[str] = []
    for row in rows:
        detail = row.get("detail") or {}
        if not isinstance(detail, dict):
            continue
        qid = str(detail.get("review_queue_id") or "").strip()
        if qid:
            queue_ids.append(qid)
    queue_meta: dict[str, dict[str, Any]] = {}
    if queue_ids:
        uniq_qids = sorted(set(queue_ids))[:2000]
        try:
            qres = (
                sb.table("dictionary_review_queue")
                .select("id,canonical,dictionary_vertical_id,dimension_6way,source_topic_id,batch_id")
                .in_("id", uniq_qids)
                .execute()
            )
            for q in qres.data or []:
                qid = str(q.get("id") or "").strip()
                if qid:
                    queue_meta[qid] = q
        except Exception:
            queue_meta = {}

    logs: list[dict[str, Any]] = []
    for row in rows:
        detail = row.get("detail") or {}
        if not isinstance(detail, dict):
            continue
        qid = str(detail.get("review_queue_id") or "").strip()
        meta = queue_meta.get(qid) if qid else None

        is_approved = "vertical_ids" in detail and "dimension_6way" in detail
        is_rejected = str(detail.get("agent_provider") or "").strip() == "dictionary-smart-merge" and (
            "reason_zh" in detail
        )
        if not is_approved and not is_rejected:
            continue

        source_topic_id = str((meta or {}).get("source_topic_id") or detail.get("source_topic_id") or "").strip()
        batch_id = str((meta or {}).get("batch_id") or detail.get("batch_id") or "").strip()
        source = source_topic_id or batch_id or "unknown"

        canonical = str(detail.get("canonical") or (meta or {}).get("canonical") or "").strip()
        vertical_id = str(
            (detail.get("vertical_ids") or [None])[0]
            or detail.get("vertical_id")
            or (meta or {}).get("dictionary_vertical_id")
            or ""
        ).strip()
        dim = str(detail.get("dimension_6way") or (meta or {}).get("dimension_6way") or "").strip() or None

        logs.append(
            {
                "at": row.get("created_at"),
                "action": "approved" if is_approved else "rejected",
                "review_queue_id": qid or None,
                "canonical": canonical or None,
                "vertical_id": vertical_id or None,
                "dimension_6way": dim,
                "source": source,
                "reason_zh": str(detail.get("reason_zh") or "").strip() or None,
            }
        )
        if len(logs) >= limit:
            break

    return {"items": logs, "limit": limit}


@router.post("/review-queue/agent-review")
def post_dictionary_agent_review_queue(
    _rbac: Annotated[str, Depends(require_mutator_role)],
    actor: Annotated[str | None, Depends(get_rsa_username_optional)] = None,
    limit: int = Query(default=50, ge=1, le=200),
    sb: Client = Depends(require_supabase),
) -> dict:
    """智能体审核：把 pending 词条送给 Agent，回写建议的 dimension_6way。"""
    settings = get_settings()
    agent_url = (settings.agent_enrichment_url or "").strip() or (
        settings.deepseek_adapter_agent_enrich_url or ""
    ).strip()
    if not agent_url:
        raise HTTPException(status_code=400, detail="未配置 AGENT_ENRICHMENT_URL 或 DEEPSEEK_ADAPTER_AGENT_ENRICH_URL")

    try:
        q = (
            sb.table("dictionary_review_queue")
            .select("*")
            .eq("status", "pending")
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"读取审核队列失败：{e!s}") from e
    rows = q.data or []
    if not rows:
        return {"ok": True, "total": 0, "reviewed": 0, "updated": 0, "items": []}

    pseudo_reviews: list[dict[str, Any]] = []
    review_ids_order: list[str] = []
    for row in rows:
        rid = str(row.get("id") or "").strip()
        if not rid:
            continue
        canonical = str(row.get("canonical") or "").strip()
        syns_raw = row.get("synonyms") or []
        syns = [str(x).strip() for x in syns_raw if str(x).strip()] if isinstance(syns_raw, list) else []
        text = f"keyword: {canonical}\nsynonyms: {', '.join(syns)}"
        pseudo_reviews.append({"id": rid, "raw_text": text, "title": canonical, "rating": None})
        review_ids_order.append(rid)

    if not pseudo_reviews:
        return {"ok": True, "total": len(rows), "reviewed": 0, "updated": 0, "items": []}

    timeout_sec = float(settings.agent_enrichment_timeout_seconds or 120.0)
    max_retries = max(1, int(settings.agent_enrichment_max_retries or 2))
    batch_size = 20
    all_agent_rows: list[dict[str, Any]] = []
    failed_batches: list[dict[str, Any]] = []

    for i in range(0, len(pseudo_reviews), batch_size):
        sub_reviews = pseudo_reviews[i : i + batch_size]
        sub_ids = review_ids_order[i : i + batch_size]
        try:
            part = call_agent_enrichment_batch(
                url=agent_url,
                api_key=settings.agent_enrichment_api_key,
                timeout=timeout_sec,
                max_retries=max_retries,
                insight_task_id="dictionary-review-queue",
                platform="dictionary",
                product_id="topic_pool",
                dictionary_vertical_id=DEFAULT_VERTICAL_ID,
                enrichment_mode="sample",
                reviews_subset=sub_reviews,
                review_ids_order=sub_ids,
            )
            all_agent_rows.extend(part)
        except AgentEnrichmentError as e:
            failed_batches.append(
                {
                    "offset": i,
                    "size": len(sub_reviews),
                    "code": e.code,
                    "message": e.message[:500],
                }
            )
        except Exception as e:  # noqa: BLE001
            failed_batches.append(
                {
                    "offset": i,
                    "size": len(sub_reviews),
                    "code": "AGENT_REVIEW_UNEXPECTED",
                    "message": str(e)[:500],
                }
            )

    if not all_agent_rows and failed_batches:
        first = failed_batches[0]
        raise HTTPException(
            status_code=502,
            detail=f"{first.get('code')}: {first.get('message')}",
        )

    by_id = {str(x.get("review_id") or ""): x for x in all_agent_rows if isinstance(x, dict)}
    updated = 0
    reviewed = 0
    items: list[dict[str, Any]] = []
    now = _utc_now_iso()

    for row in rows:
        qid = str(row.get("id") or "").strip()
        pred = by_id.get(qid)
        if not pred:
            continue
        reviewed += 1
        suggest_dim = _pick_agent_dimension(pred)
        before_dim = (row.get("dimension_6way") or "").strip() or None
        if suggest_dim and suggest_dim != before_dim:
            try:
                sb.table("dictionary_review_queue").update(
                    {"dimension_6way": suggest_dim, "updated_at": now}
                ).eq("id", qid).eq("status", "pending").execute()
                updated += 1
            except Exception:  # noqa: BLE001
                pass
        try_record_audit(
            sb,
            username=audit_actor_name(actor),
            menu_key="smart-mining",
            message=f"智能体审核词条：{row.get('canonical')}",
            detail=_audit_detail(
                event_type="topic_agent_review_item",
                action="review",
                entity="dictionary_review_queue",
                source="deepseek-adapter",
                extra={
                    "review_queue_id": qid,
                    "canonical": row.get("canonical"),
                    "synonyms": row.get("synonyms") or [],
                    "before_dimension_6way": before_dim,
                    "suggested_dimension_6way": suggest_dim,
                    "agent_provider": "deepseek-adapter",
                },
            ),
        )
        items.append(
            {
                "id": qid,
                "canonical": row.get("canonical"),
                "before_dimension_6way": before_dim,
                "suggested_dimension_6way": suggest_dim,
            }
        )

    try_record_audit(
        sb,
        username=audit_actor_name(actor),
        menu_key="smart-mining",
        message=f"智能体审核队列：reviewed={reviewed} updated={updated}",
        detail=_audit_detail(
            event_type="topic_agent_review_batch",
            action="review",
            entity="dictionary_review_queue",
            source="deepseek-adapter",
            counts={"reviewed": reviewed, "updated": updated, "limit": limit, "total": len(rows)},
        ),
    )

    return {
        "ok": True,
        "total": len(rows),
        "reviewed": reviewed,
        "updated": updated,
        "items": items,
        "failed_batches": failed_batches,
    }


@router.post("/review-queue/smart-merge")
def post_dictionary_review_queue_smart_merge(
    body: DictionarySmartMergeRequest,
    _rbac: Annotated[str, Depends(require_mutator_role)],
    actor: Annotated[str | None, Depends(get_rsa_username_optional)] = None,
    sb: Client = Depends(require_supabase),
) -> dict:
    """智能合并：按词典+维度将多条队列词条交给模型，合并/清洗同义词，不适合收录的标为 kind=rejected。"""
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

    qid_list = [str(_parse_queue_uuid(q)) for q in body.queue_ids]
    expected_ids = set(qid_list)

    try:
        res = sb.table("dictionary_review_queue").select("*").in_("id", qid_list).execute()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"读取审核队列失败：{e!s}") from e
    rows = res.data or []
    if len(rows) != len(expected_ids):
        raise HTTPException(status_code=400, detail="部分 queue_id 不存在或重复")

    for r in rows:
        if str(r.get("status") or "") != "pending":
            raise HTTPException(status_code=400, detail=f"队列项非 pending：{r.get('id')}")
        rv = (str(r.get("dictionary_vertical_id") or "").strip() or DEFAULT_VERTICAL_ID)
        if rv != vid:
            raise HTTPException(status_code=400, detail="vertical_id 与队列项不一致")
        rd = str(r.get("dimension_6way") or "").strip().lower()
        if rd != dim:
            raise HTTPException(status_code=400, detail="dimension_6way 与队列项不一致")

    payload: dict[str, Any] = {
        "dictionary_vertical_id": vid,
        "dictionary_label_zh": _vertical_label_zh(vid),
        "dimension_6way": dim,
        "items": [
            {
                "queue_id": str(r["id"]),
                "canonical": str(r.get("canonical") or "").strip(),
                "synonyms": _normalize_synonyms_json(r.get("synonyms")),
            }
            for r in rows
        ],
    }

    try:
        merged = load_merged_entries_for_vertical(vid, sb=sb)
    except Exception:  # noqa: BLE001
        merged = []
    existing_slice: list[dict[str, Any]] = []
    for e in merged:
        if not isinstance(e, dict):
            continue
        d = str(e.get("dimension_6way") or "").strip().lower()
        if d != dim:
            continue
        can = str(e.get("canonical") or "").strip()
        if not can:
            continue
        existing_slice.append(
            {
                "canonical": can,
                "aliases": _normalize_synonyms_json(e.get("aliases")),
            }
        )
    total_existing = len(existing_slice)
    max_exist = 400
    if total_existing > max_exist:
        payload["existing_dictionary_entries"] = existing_slice[:max_exist]
        payload["existing_dictionary_total"] = total_existing
        payload["existing_dictionary_truncated"] = True
    elif total_existing:
        payload["existing_dictionary_entries"] = existing_slice
        payload["existing_dictionary_total"] = total_existing

    existing_ctx_sent = len(payload.get("existing_dictionary_entries") or [])
    existing_ctx_total = int(payload.get("existing_dictionary_total") or 0)
    existing_ctx_truncated = bool(payload.get("existing_dictionary_truncated"))

    timeout = min(240.0, max(60.0, float(settings.agent_enrichment_timeout_seconds or 120.0) * 1.5))
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=payload, headers=_adapter_auth_headers(settings))
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"智能合并服务不可达：{e!s}") from e
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"智能合并服务错误 HTTP {resp.status_code}: {resp.text[:1200]}",
        )
    try:
        outer = resp.json()
    except ValueError as e:
        raise HTTPException(status_code=502, detail=f"智能合并响应非 JSON：{e!s}") from e
    if not isinstance(outer, dict):
        raise HTTPException(status_code=502, detail="智能合并响应格式错误")
    plan = outer.get("plan")
    if not isinstance(plan, dict):
        raise HTTPException(status_code=502, detail="智能合并响应缺少 plan")

    _validate_smart_merge_plan(plan, expected_ids)

    now = _utc_now_iso()
    merge_groups = plan.get("merge_groups") or []
    updates = plan.get("updates") or []
    rejects = plan.get("rejects") or []

    merged_keeps = 0
    updated_rows = 0
    deleted_drops = 0
    rejected_n = 0

    for mg in merge_groups:
        if not isinstance(mg, dict):
            continue
        keep = str(mg.get("keep_queue_id") or "").strip()
        drops = [str(x).strip() for x in (mg.get("drop_queue_ids") or []) if str(x).strip()]
        canon = str(mg.get("canonical") or "").strip()
        syns = _normalize_synonyms_json(mg.get("synonyms"))
        if len(canon) < 2 or not syns:
            raise HTTPException(status_code=502, detail="merge_groups 中 canonical/synonyms 无效")
        try:
            sb.table("dictionary_review_queue").update(
                {"canonical": canon, "synonyms": syns, "updated_at": now}
            ).eq("id", keep).eq("status", "pending").execute()
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=502, detail=f"更新 merge keep 失败：{e!s}") from e
        merged_keeps += 1
        for d in drops:
            try:
                sb.table("dictionary_review_queue").delete().eq("id", d).eq("status", "pending").execute()
            except Exception as e:  # noqa: BLE001
                raise HTTPException(status_code=502, detail=f"删除 merge drop 失败：{e!s}") from e
            deleted_drops += 1

    for u in updates:
        if not isinstance(u, dict):
            continue
        qid = str(u.get("queue_id") or "").strip()
        canon = str(u.get("canonical") or "").strip()
        syns = _normalize_synonyms_json(u.get("synonyms"))
        if len(canon) < 2 or not syns:
            raise HTTPException(status_code=502, detail=f"updates 项无效：{qid}")
        try:
            sb.table("dictionary_review_queue").update(
                {"canonical": canon, "synonyms": syns, "updated_at": now}
            ).eq("id", qid).eq("status", "pending").execute()
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=502, detail=f"更新队列失败：{e!s}") from e
        updated_rows += 1

    for rj in rejects:
        if not isinstance(rj, dict):
            continue
        qid = str(rj.get("queue_id") or "").strip()
        reason = str(rj.get("reason_zh") or "").strip()[:500]
        try:
            sb.table("dictionary_review_queue").update(
                {"kind": "rejected", "updated_at": now}
            ).eq("id", qid).eq("status", "pending").execute()
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=502, detail=f"驳回失败：{e!s}") from e
        rejected_n += 1
        try_record_audit(
            sb,
            username=audit_actor_name(actor),
            menu_key="smart-mining",
            message=f"智能合并驳回：{qid}",
            detail=_audit_detail(
                event_type="topic_smart_merge_reject",
                action="reject",
                entity="dictionary_review_queue",
                source="dictionary-smart-merge",
                extra={
                    "review_queue_id": qid,
                    "vertical_id": vid,
                    "dimension_6way": dim,
                    "reason_zh": reason,
                    "agent_provider": "dictionary-smart-merge",
                },
            ),
        )

    try_record_audit(
        sb,
        username=audit_actor_name(actor),
        menu_key="smart-mining",
        message=f"智能合并完成：merge_keeps={merged_keeps} drops={deleted_drops} updates={updated_rows} rejects={rejected_n}",
        detail=_audit_detail(
            event_type="topic_smart_merge_batch",
            action="merge",
            entity="dictionary_review_queue",
            source="dictionary-smart-merge",
            counts={
                "merge_keeps": merged_keeps,
                "merge_drops_deleted": deleted_drops,
                "updates": updated_rows,
                "rejects": rejected_n,
                "queue_count": len(expected_ids),
            },
            extra={
                "vertical_id": vid,
                "dimension_6way": dim,
                "queue_ids": sorted(expected_ids),
            },
        ),
    )

    return {
        "ok": True,
        "vertical_id": vid,
        "dimension_6way": dim,
        "merge_keeps": merged_keeps,
        "merge_drops_deleted": deleted_drops,
        "updates": updated_rows,
        "rejects": rejected_n,
        "existing_dictionary_context_sent": existing_ctx_sent,
        "existing_dictionary_context_total": existing_ctx_total,
        "existing_dictionary_context_truncated": existing_ctx_truncated,
    }
