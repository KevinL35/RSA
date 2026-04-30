from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from app.core.rbac import get_rsa_role, get_rsa_username_optional, require_mutator_role
from app.core.config import Settings, get_settings
from app.integrations.agent_enrichment.client import (
    AgentEnrichmentError,
    call_agent_enrichment_batch,
)
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
from .verticals import DEFAULT_VERTICAL_ID, DICTIONARY_VERTICALS, assert_valid_vertical_id

router = APIRouter(prefix="/api/v1/dictionary", tags=["dictionary"])
_SIX_DIMS = set(SIX_WAY_DIMENSION_ORDER)


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
        "vertical_id": (row.get("dictionary_vertical_id") or DEFAULT_VERTICAL_ID).strip() or DEFAULT_VERTICAL_ID,
        "dimension_6way": dim.strip() if isinstance(dim, str) and dim.strip() else None,
        "batch_id": row.get("batch_id"),
        "source_topic_id": row.get("source_topic_id"),
        "quality_score": row.get("quality_score"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def _parse_queue_uuid(queue_id: str) -> uuid.UUID:
    try:
        return uuid.UUID((queue_id or "").strip())
    except ValueError as e:
        raise HTTPException(status_code=400, detail="无效队列 id") from e


def _pick_agent_dimension(item: dict[str, Any]) -> str | None:
    dims = item.get("dimensions")
    if not isinstance(dims, list) or not dims:
        return None
    best_dim: str | None = None
    best_score = -1
    for d in dims:
        if not isinstance(d, dict):
            continue
        dim = str(d.get("dimension") or "").strip().lower()
        if dim not in _SIX_DIMS:
            continue
        kws = d.get("keywords")
        kw_count = len(kws) if isinstance(kws, list) else 0
        score = kw_count
        if score > best_score:
            best_score = score
            best_dim = dim
    return best_dim


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


def _dedupe_synonyms_for_queue(synonyms: list[str], *, exclude_canonical: str) -> list[str]:
    """去重、去空、去掉与关键词同写法的同义词（大小写不敏感）。"""
    seen: set[str] = set()
    out: list[str] = []
    ex = exclude_canonical.strip().lower()
    for raw in synonyms:
        s = str(raw).strip()
        if not s or s.lower() == ex:
            continue
        k = s.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(s)
        if len(out) >= 80:
            break
    return out


class CreateDictionaryReviewQueueBody(BaseModel):
    """人工新增主题：写入待审队列（与挖掘结果同源）。"""

    canonical: str = Field(min_length=2, max_length=512)
    synonyms: list[str] = Field(min_length=1, max_length=80)
    vertical_id: str | None = Field(default=None, max_length=64)


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

        # 智能体审核事件
        if "suggested_dimension_6way" in detail:
            item["agent_reviewed_at"] = row.get("created_at")
            item["suggested_dimension_6way"] = detail.get("suggested_dimension_6way")
            syns = detail.get("synonyms")
            if isinstance(syns, list):
                item["synonyms"] = [str(x).strip() for x in syns if str(x).strip()]

        # 人工通过事件
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


def _adapter_auth_headers(settings: Settings) -> dict[str, str]:
    headers: dict[str, str] = {"Content-Type": "application/json", "Accept": "application/json"}
    key = (
        (settings.agent_enrichment_api_key or "").strip()
        or (settings.insight_summary_api_key or "").strip()
        or (settings.analysis_provider_api_key or "").strip()
    )
    if key:
        headers["Authorization"] = f"Bearer {key}"
    return headers


def _vertical_label_zh(vid: str) -> str:
    for v in DICTIONARY_VERTICALS:
        if v["id"] == vid:
            return str(v.get("label_zh") or vid)
    return vid


def _audit_detail(
    *,
    event_type: str,
    action: str,
    entity: str,
    result: str = "success",
    source: str | None = None,
    counts: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """统一审计 detail 字段，便于按事件检索与复盘。"""
    out: dict[str, Any] = {
        "event_type": event_type,
        "action": action,
        "entity": entity,
        "result": result,
    }
    if source:
        out["source"] = source
    if counts:
        out["counts"] = counts
    if extra:
        out.update(extra)
    return out


def _validate_smart_merge_plan(plan: dict[str, Any], expected_ids: set[str]) -> None:
    if not isinstance(plan, dict):
        raise HTTPException(status_code=502, detail="智能合并返回 plan 非对象")
    updates = plan.get("updates")
    rejects = plan.get("rejects")
    merge_groups = plan.get("merge_groups")
    if not isinstance(updates, list) or not isinstance(rejects, list) or not isinstance(merge_groups, list):
        raise HTTPException(status_code=502, detail="plan 缺少 updates/rejects/merge_groups 数组")

    covered: set[str] = set()

    for i, mg in enumerate(merge_groups):
        if not isinstance(mg, dict):
            raise HTTPException(status_code=502, detail=f"merge_groups[{i}] 非对象")
        keep = str(mg.get("keep_queue_id") or "").strip()
        drops_raw = mg.get("drop_queue_ids") or []
        if not keep or not isinstance(drops_raw, list):
            raise HTTPException(status_code=502, detail=f"merge_groups[{i}] 缺少 keep_queue_id 或 drop_queue_ids")
        drops = [str(x).strip() for x in drops_raw if str(x).strip()]
        for x in [keep, *drops]:
            if x not in expected_ids:
                raise HTTPException(status_code=502, detail=f"merge_groups 含未知 queue_id：{x!r}")
            if x in covered:
                raise HTTPException(status_code=502, detail=f"queue_id 重复覆盖：{x!r}")
            covered.add(x)

    for i, u in enumerate(updates):
        if not isinstance(u, dict):
            raise HTTPException(status_code=502, detail=f"updates[{i}] 非对象")
        qid = str(u.get("queue_id") or "").strip()
        if not qid or qid not in expected_ids:
            raise HTTPException(status_code=502, detail=f"updates 无效 queue_id：{qid!r}")
        if qid in covered:
            raise HTTPException(status_code=502, detail=f"queue_id 重复覆盖：{qid!r}")
        covered.add(qid)

    for i, rj in enumerate(rejects):
        if not isinstance(rj, dict):
            raise HTTPException(status_code=502, detail=f"rejects[{i}] 非对象")
        qid = str(rj.get("queue_id") or "").strip()
        if not qid or qid not in expected_ids:
            raise HTTPException(status_code=502, detail=f"rejects 无效 queue_id：{qid!r}")
        if qid in covered:
            raise HTTPException(status_code=502, detail=f"queue_id 重复覆盖：{qid!r}")
        covered.add(qid)

    if covered != expected_ids:
        missing = sorted(expected_ids - covered)
        extra = sorted(covered - expected_ids)
        raise HTTPException(
            status_code=502,
            detail=f"智能合并 plan 未覆盖全部 queue_id missing={missing[:8]} extra={extra[:8]}",
        )


class DictionarySmartMergeRequest(BaseModel):
    vertical_id: str = Field(min_length=1, max_length=64)
    dimension_6way: str = Field(min_length=1, max_length=64)
    queue_ids: list[str] = Field(min_length=1, max_length=120)


class DictionaryTaxonomyAgentReviewRequest(BaseModel):
    vertical_id: str = Field(min_length=1, max_length=64)
    dimension_6way: str = Field(min_length=1, max_length=64)


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

    # 同一词典、同一六维下「已入库」词条，供模型对照去重（只读；模型仍只能改 items 里的 queue_id）
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
        # postgrest 2.x：.eq() 后为 FilterRequestBuilder，不可再 .select()；默认 Prefer: return=representation
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


class RejectSynonymBody(BaseModel):
    vertical_id: str = Field(min_length=1, max_length=64)
    dimension_6way: str = Field(min_length=1, max_length=64)
    canonical: str = Field(min_length=1, max_length=512)
    alias: str = Field(min_length=1, max_length=512)


def _remove_alias_from_overlay(
    sb: Client,
    *,
    vertical_id: str,
    dimension_6way: str,
    canonical: str,
    alias: str,
) -> dict[str, Any]:
    """
    从 taxonomy_entries（overlay）中找到 (vertical, dim, canonical) 对应行并去掉 alias。
    aliases 为空后整行删除（避免词典管理出现 0 同义词的孤词条）。
    返回 { matched, removed, remaining_aliases, entry_id, entry_deleted }。
    """
    canon_norm = canonical.strip().lower()
    alias_norm = alias.strip().lower()
    try:
        res = (
            sb.table("taxonomy_entries")
            .select("id, aliases, canonical")
            .eq("source_layer", "overlay")
            .eq("dictionary_vertical_id", vertical_id)
            .eq("dimension_6way", dimension_6way)
            .eq("canonical_norm", canon_norm)
            .limit(1)
            .execute()
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"查询 taxonomy_entries 失败：{e!s}") from e
    rows = res.data or []
    if not rows:
        return {
            "matched": False,
            "removed": False,
            "remaining_aliases": [],
            "entry_id": None,
            "entry_deleted": False,
        }
    row = rows[0]
    raw_aliases = row.get("aliases") or []
    if not isinstance(raw_aliases, list):
        raw_aliases = []
    next_aliases: list[str] = []
    removed = False
    for a in raw_aliases:
        s = str(a).strip()
        if not s:
            continue
        if s.lower() == alias_norm:
            removed = True
            continue
        next_aliases.append(s)
    if not removed:
        return {
            "matched": True,
            "removed": False,
            "remaining_aliases": next_aliases,
            "entry_id": row.get("id"),
            "entry_deleted": False,
        }
    entry_deleted = False
    try:
        if not next_aliases:
            sb.table("taxonomy_entries").delete().eq("id", row["id"]).execute()
            entry_deleted = True
        else:
            sb.table("taxonomy_entries").update(
                {"aliases": next_aliases, "updated_at": _utc_now_iso()}
            ).eq("id", row["id"]).execute()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"更新 taxonomy_entries 失败：{e!s}") from e
    return {
        "matched": True,
        "removed": True,
        "remaining_aliases": next_aliases,
        "entry_id": row.get("id"),
        "entry_deleted": entry_deleted,
    }


def _enqueue_rejected_alias_for_review(
    sb: Client,
    *,
    vertical_id: str,
    dimension_6way: str,
    canonical: str,
    alias: str,
    actor_username: str | None,
) -> dict[str, Any]:
    """
    把被驳回的同义词回流到 dictionary_review_queue：
      - canonical = 原词典关键词（不变）
      - synonyms = 当前已驳回的若干同义词（来源同 canonical 时自动合并去重）
      - kind = 'rejected'
    返回 { id, action, synonyms }，action ∈ {'inserted','merged','noop'}。
    """
    keyword = canonical.strip()
    al = alias.strip()
    if not keyword or not al:
        return {"id": None, "action": "noop", "synonyms": []}
    try:
        existed = (
            sb.table("dictionary_review_queue")
            .select("id, synonyms, kind")
            .eq("status", "pending")
            .eq("dictionary_vertical_id", vertical_id)
            .eq("dimension_6way", dimension_6way)
            .ilike("canonical", keyword)
            .limit(1)
            .execute()
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"查询 dictionary_review_queue 失败：{e!s}") from e
    existed_rows = existed.data or []
    if existed_rows:
        cur = existed_rows[0]
        cur_syn_raw = cur.get("synonyms") or []
        cur_syn: list[str] = (
            [str(x).strip() for x in cur_syn_raw if str(x).strip()]
            if isinstance(cur_syn_raw, list)
            else []
        )
        if any(s.lower() == al.lower() for s in cur_syn):
            return {"id": str(cur["id"]), "action": "noop", "synonyms": cur_syn}
        next_syn = [*cur_syn, al]
        try:
            sb.table("dictionary_review_queue").update(
                {
                    "synonyms": next_syn,
                    "kind": "rejected",
                    "updated_at": _utc_now_iso(),
                }
            ).eq("id", cur["id"]).execute()
        except Exception as e:  # noqa: BLE001
            raise HTTPException(
                status_code=502, detail=f"合并 dictionary_review_queue 失败：{e!s}"
            ) from e
        return {"id": str(cur["id"]), "action": "merged", "synonyms": next_syn}
    payload = {
        "kind": "rejected",
        "canonical": keyword,
        "synonyms": [al],
        "dictionary_vertical_id": vertical_id,
        "dimension_6way": dimension_6way,
        "batch_id": f"reject:{vertical_id}",
        "source_topic_id": f"reject-from:{keyword}",
        "status": "pending",
    }
    try:
        ins = sb.table("dictionary_review_queue").insert(payload).execute()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"写入 dictionary_review_queue 失败：{e!s}") from e
    rows = ins.data or []
    rid = str(rows[0].get("id") or "") if rows else ""
    return {"id": rid or None, "action": "inserted" if rid else "noop", "synonyms": [al]}


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
