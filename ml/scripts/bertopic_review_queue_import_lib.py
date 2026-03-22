"""BERTopic 候选 → Supabase dictionary_review_queue（供 CLI 与 bertopic-api 共用）。"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

_VALID_DIMENSIONS = frozenset(
    {
        "pros",
        "cons",
        "return_reasons",
        "purchase_motivation",
        "user_expectation",
        "usage_scenario",
    },
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_platform_api_dotenv() -> None:
    p = repo_root() / "apps" / "platform-api" / ".env"
    if not p.is_file():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, _, v = s.partition("=")
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def http_json(
    method: str,
    url: str,
    *,
    key: str,
    body: object | None = None,
    extra_headers: dict[str, str] | None = None,
) -> tuple[int, str]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
    }
    if data is not None:
        headers["Content-Type"] = "application/json"
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        return e.code, raw


def pending_exists(base: str, key: str, batch_id: str, source_topic_id: str) -> bool:
    q = urllib.parse.urlencode(
        {
            "batch_id": f"eq.{batch_id}",
            "source_topic_id": f"eq.{source_topic_id}",
            "status": "eq.pending",
            "select": "id",
            "limit": "1",
        }
    )
    url = f"{base.rstrip('/')}/rest/v1/dictionary_review_queue?{q}"
    code, raw = http_json("GET", url, key=key)
    if code != 200:
        return False
    try:
        rows = json.loads(raw) if raw.strip() else []
    except json.JSONDecodeError:
        return False
    return isinstance(rows, list) and len(rows) > 0


def normalize_synonyms(canonical: str, aliases: object) -> list[str]:
    c_low = canonical.strip().lower()
    out: list[str] = []
    seen: set[str] = set()
    if not isinstance(aliases, list):
        return out
    for a in aliases:
        s = str(a).strip()
        if not s or s.lower() == c_low:
            continue
        if s.lower() in seen:
            continue
        seen.add(s.lower())
        out.append(s)
    return out


def build_queue_payloads_from_candidate_rows(
    rows: list[dict],
    *,
    vertical_id: str = "general",
    kind: str = "new_discovery",
) -> tuple[list[dict], list[str]]:
    """将 TA-9 候选 dict 列表转为 REST POST 体；返回 (payloads, warnings)。"""
    vertical_id = vertical_id.strip() or "general"
    payloads: list[dict] = []
    warnings: list[str] = []

    for i, row in enumerate(rows, start=1):
        suggested = str(row.get("suggested_canonical") or "").strip()
        if len(suggested) < 2:
            warnings.append(f"第 {i} 条 suggested_canonical 过短，已跳过")
            continue

        batch_id = str(row.get("batch_id") or "").strip() or None
        source_topic_id = str(row.get("source_topic_id") or "").strip() or None
        if not batch_id or not source_topic_id:
            warnings.append(f"第 {i} 条缺少 batch_id 或 source_topic_id，已跳过")
            continue

        aliases = normalize_synonyms(suggested, row.get("aliases"))
        dim = row.get("dimension_6way")
        dim_s = dim.strip().lower() if isinstance(dim, str) and dim.strip() else None
        if dim_s is not None and dim_s not in _VALID_DIMENSIONS:
            warnings.append(f"第 {i} 条 dimension_6way 无效 {dim_s!r}，已置空")
            dim_s = None

        qs = row.get("quality_score")
        quality: float | None
        if isinstance(qs, (int, float)):
            quality = float(qs)
        else:
            quality = None

        rec: dict = {
            "kind": kind,
            "canonical": suggested,
            "synonyms": aliases,
            "dictionary_vertical_id": vertical_id,
            "dimension_6way": dim_s,
            "batch_id": batch_id,
            "source_topic_id": source_topic_id,
            "status": "pending",
        }
        if quality is not None:
            rec["quality_score"] = quality
        payloads.append(rec)

    return payloads, warnings


def import_payloads_to_dictionary_review_queue(
    payloads: list[dict],
    *,
    skip_existing: bool,
    supabase_url: str,
    service_role_key: str,
) -> tuple[int, int, str | None]:
    """
    逐条 POST 到 dictionary_review_queue。
    返回 (inserted, skipped, error_message)；error_message 非空表示中途失败已中止。
    """
    base = supabase_url.strip().rstrip("/")
    key = service_role_key.strip()
    url = f"{base}/rest/v1/dictionary_review_queue"
    inserted = 0
    skipped = 0
    for p in payloads:
        if skip_existing and pending_exists(base, key, p["batch_id"], p["source_topic_id"]):
            skipped += 1
            continue
        code, raw = http_json(
            "POST",
            url,
            key=key,
            body=p,
            extra_headers={"Prefer": "return=minimal"},
        )
        if code not in (200, 201):
            return inserted, skipped, f"HTTP {code}: {raw[:500]}"
        inserted += 1
    return inserted, skipped, None
