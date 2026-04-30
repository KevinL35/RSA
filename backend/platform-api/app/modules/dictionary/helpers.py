from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from supabase import Client

from app.core.config import Settings
from .taxonomy_yaml import SIX_WAY_DIMENSION_ORDER
from .verticals import DEFAULT_VERTICAL_ID, DICTIONARY_VERTICALS, VERTICAL_IDS

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
