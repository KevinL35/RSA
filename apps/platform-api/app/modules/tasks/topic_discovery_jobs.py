"""
主题挖掘后台任务（topic_discovery_jobs）：
- POST 创建一行 status='pending' 的 job，立刻返回；
- 子线程 spawn ml/topic_mining/scripts/bertopic_supabase_pools.py 子进程，写入 pid/pgid；
- 子进程结束后写入 status='success|failed' + summary/error_message；
- 取消：根据 pgid 杀进程组（fallback 杀 pid），并把 status 标 cancelled。

前端通过 GET .../jobs/latest 轮询；与 dev.sh 一起启动后即可使用。
"""

from __future__ import annotations

import json
import logging
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

log = logging.getLogger("rsa.topic_jobs")

# apps/platform-api/app/modules/tasks/topic_discovery_jobs.py → 仓库根 = parents[5]
_REPO_ROOT = Path(__file__).resolve().parents[5]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_topic_python() -> str:
    """优先 TOPIC_MINING_PYTHON；否则尝试常见 venv；否则 sys.executable。"""
    env = (os.environ.get("TOPIC_MINING_PYTHON") or "").strip()
    if env:
        return env
    candidates = [
        _REPO_ROOT / ".venv-topic" / "bin" / "python",
        _REPO_ROOT / ".venv-bertopic" / "bin" / "python",
        _REPO_ROOT / "ml" / ".venv-topic" / "bin" / "python",
        _REPO_ROOT / "ml" / ".venv-bertopic" / "bin" / "python",
    ]
    for p in candidates:
        try:
            if p.is_file() and os.access(p, os.X_OK):
                return str(p)
        except OSError:
            continue
    return sys.executable


def _supabase():
    from app.integrations.supabase import require_supabase

    return require_supabase()


def create_job(
    sb: Any,
    *,
    insight_task_id: UUID | None,
    embedding_model: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    """insight_task_id=None 表示全局（在三总表上跨任务挖掘）。"""
    job_id = str(uuid4())
    row = {
        "id": job_id,
        "insight_task_id": str(insight_task_id) if insight_task_id else None,
        "status": "pending",
        "embedding_model": embedding_model,
        "summary": None,
        "started_at": None,
        "finished_at": None,
    }
    res = sb.table("topic_discovery_jobs").insert(row).execute()
    inserted = (res.data or [row])[0]
    threading.Thread(
        target=_run_in_thread,
        args=(
            job_id,
            str(insight_task_id) if insight_task_id else None,
            embedding_model,
            dry_run,
        ),
        daemon=True,
        name=f"topic-job-{job_id[:8]}",
    ).start()
    return inserted


def get_job(sb: Any, job_id: UUID) -> dict[str, Any] | None:
    res = (
        sb.table("topic_discovery_jobs")
        .select("*")
        .eq("id", str(job_id))
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def get_latest_for_task(sb: Any, insight_task_id: UUID) -> dict[str, Any] | None:
    res = (
        sb.table("topic_discovery_jobs")
        .select("*")
        .eq("insight_task_id", str(insight_task_id))
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def get_latest_global(sb: Any) -> dict[str, Any] | None:
    """最新一条全局（insight_task_id IS NULL）主题挖掘任务。"""
    res = (
        sb.table("topic_discovery_jobs")
        .select("*")
        .is_("insight_task_id", "null")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def get_latest_active_any(sb: Any) -> dict[str, Any] | None:
    """全表中最近一条 pending/running 任务（用于阻止并发）。"""
    res = (
        sb.table("topic_discovery_jobs")
        .select("*")
        .in_("status", ["pending", "running"])
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def cancel_job(sb: Any, job_id: UUID) -> dict[str, Any]:
    job = get_job(sb, job_id)
    if not job:
        raise ValueError(f"job not found: {job_id}")
    status = job.get("status")
    if status not in ("pending", "running"):
        return job

    pgid = job.get("pgid")
    pid = job.get("pid")
    killed = False
    if pgid:
        try:
            os.killpg(int(pgid), signal.SIGTERM)
            killed = True
        except (ProcessLookupError, PermissionError, OSError):
            pass
    if not killed and pid:
        try:
            os.kill(int(pid), signal.SIGTERM)
            killed = True
        except (ProcessLookupError, PermissionError, OSError):
            pass

    now = _utc_now_iso()
    sb.table("topic_discovery_jobs").update(
        {
            "status": "cancelled",
            "finished_at": now,
            "updated_at": now,
            "error_message": "cancelled by user",
        }
    ).eq("id", str(job_id)).execute()
    return get_job(sb, job_id) or {**job, "status": "cancelled"}


_POOL_DEFAULT_DIM: dict[str, str] = {
    "topic_pool_pain": "cons",
    "topic_pool_highlight": "pros",
    "topic_pool_observation": "usage_scenario",
}
_IMPORT_MAX_PER_POOL = 20


def import_topic_pool_to_review_queue(
    sb: Any, batch_id: str | None, *, max_per_pool: int = _IMPORT_MAX_PER_POOL
) -> int:
    """把指定 batch 的 BERTopic 三池候选导入 dictionary_review_queue（status=pending），
    供「主题挖掘」页面审核入库。
    - 默认六维：highlight→pros / pain→cons / observation→usage_scenario，可在审核页修改。
    - 默认词典类目 general。
    - 同 batch + 同 canonical 去重，且与 dictionary_review_queue 中现有 pending 同名词条去重。
    返回成功插入条数。
    """
    if not batch_id:
        return 0
    rows_to_insert: list[dict[str, Any]] = []
    for table_name, dim in _POOL_DEFAULT_DIM.items():
        try:
            r = (
                sb.table(table_name)
                .select("suggested_canonical,aliases,quality_score,source_topic_id")
                .eq("batch_id", batch_id)
                .order("quality_score", desc=True)
                .limit(max_per_pool)
                .execute()
            )
        except Exception:  # noqa: BLE001
            continue
        for row in r.data or []:
            canonical = (row.get("suggested_canonical") or "").strip()
            if not canonical:
                continue
            aliases = row.get("aliases") or []
            if not isinstance(aliases, list) or not aliases:
                continue
            rows_to_insert.append(
                {
                    "kind": "new_discovery",
                    "canonical": canonical,
                    "synonyms": aliases,
                    "dictionary_vertical_id": "general",
                    "dimension_6way": dim,
                    "batch_id": batch_id,
                    "source_topic_id": str(row.get("source_topic_id") or ""),
                    "quality_score": row.get("quality_score"),
                    "status": "pending",
                }
            )
    if not rows_to_insert:
        return 0
    # 同批次内去重 canonical（小写）
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for r in rows_to_insert:
        key = r["canonical"].strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    # 跳过队列中已存在 pending 同名（避免每次跑都重复入队）
    try:
        existing = (
            sb.table("dictionary_review_queue")
            .select("canonical")
            .eq("status", "pending")
            .in_("canonical", [r["canonical"] for r in deduped])
            .execute()
        )
        existing_set = {
            (r.get("canonical") or "").strip().lower() for r in (existing.data or [])
        }
    except Exception:  # noqa: BLE001
        existing_set = set()
    final_rows = [r for r in deduped if r["canonical"].strip().lower() not in existing_set]
    if not final_rows:
        return 0
    try:
        sb.table("dictionary_review_queue").insert(final_rows).execute()
    except Exception:  # noqa: BLE001
        log.exception("topic-pool-import: insert failed")
        return 0
    return len(final_rows)


def _parse_summary(stdout: str) -> dict[str, Any] | None:
    s = (stdout or "").strip()
    if not s:
        return None
    try:
        for line in reversed(s.splitlines()):
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                return json.loads(line)
        return json.loads(s)
    except (json.JSONDecodeError, ValueError):
        return None


def _run_in_thread(
    job_id: str,
    insight_task_id: str | None,
    embedding_model: str,
    dry_run: bool,
) -> None:
    try:
        sb = _supabase()
    except Exception:
        log.exception("topic-job %s: supabase 不可用，无法运行", job_id)
        return

    script = _REPO_ROOT / "ml" / "topic_mining" / "scripts" / "bertopic_supabase_pools.py"
    if not script.is_file():
        sb.table("topic_discovery_jobs").update(
            {
                "status": "failed",
                "finished_at": _utc_now_iso(),
                "updated_at": _utc_now_iso(),
                "error_message": f"未找到脚本: {script}",
            }
        ).eq("id", job_id).execute()
        return

    py = _resolve_topic_python()
    cmd = [py, str(script), "--embedding-model", embedding_model]
    if insight_task_id:
        cmd.extend(["--insight-task-id", insight_task_id])
    if dry_run:
        cmd.append("--dry-run")

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(_REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=os.environ.copy(),
            start_new_session=True,
        )
    except Exception as e:
        sb.table("topic_discovery_jobs").update(
            {
                "status": "failed",
                "finished_at": _utc_now_iso(),
                "updated_at": _utc_now_iso(),
                "error_message": f"子进程启动失败: {e!s}",
            }
        ).eq("id", job_id).execute()
        return

    try:
        pgid = os.getpgid(proc.pid)
    except OSError:
        pgid = None

    sb.table("topic_discovery_jobs").update(
        {
            "status": "running",
            "pid": proc.pid,
            "pgid": pgid,
            "started_at": _utc_now_iso(),
            "updated_at": _utc_now_iso(),
        }
    ).eq("id", job_id).execute()

    try:
        stdout, stderr = proc.communicate()
    except Exception as e:
        try:
            proc.kill()
        except Exception:
            pass
        sb.table("topic_discovery_jobs").update(
            {
                "status": "failed",
                "finished_at": _utc_now_iso(),
                "updated_at": _utc_now_iso(),
                "error_message": f"等待子进程异常: {e!s}",
            }
        ).eq("id", job_id).execute()
        return

    # 若期间被取消，避免覆盖 cancelled 状态
    cur = get_job(sb, UUID(job_id))
    if cur and cur.get("status") == "cancelled":
        return

    now = _utc_now_iso()
    if proc.returncode == 0:
        summary = _parse_summary(stdout)
        batch_id = None
        if isinstance(summary, dict):
            batch_id = summary.get("batch_id")
        sb.table("topic_discovery_jobs").update(
            {
                "status": "success",
                "summary": summary,
                "batch_id": batch_id,
                "finished_at": now,
                "updated_at": now,
            }
        ).eq("id", job_id).execute()
        # 自动把本批 topic_pool_* 候选导入审核队列；失败仅记日志，不影响 job 状态
        try:
            inserted = import_topic_pool_to_review_queue(sb, batch_id)
            if inserted:
                log.info(
                    "topic-job %s: imported %d candidates from batch=%s into dictionary_review_queue",
                    job_id,
                    inserted,
                    batch_id,
                )
        except Exception:  # noqa: BLE001
            log.exception("topic-job %s: import_topic_pool_to_review_queue failed", job_id)
    else:
        # SIGTERM/SIGKILL 退出码视为 cancelled
        if proc.returncode in (-signal.SIGTERM, -signal.SIGKILL, 143, 137):
            sb.table("topic_discovery_jobs").update(
                {
                    "status": "cancelled",
                    "finished_at": now,
                    "updated_at": now,
                    "error_message": (stderr or "")[:4000] or "terminated",
                }
            ).eq("id", job_id).execute()
        else:
            err = (stderr or stdout or f"exit {proc.returncode}").strip()
            sb.table("topic_discovery_jobs").update(
                {
                    "status": "failed",
                    "finished_at": now,
                    "updated_at": now,
                    "error_message": err[:4000],
                }
            ).eq("id", job_id).execute()
    # 留点时间让最后一行写入完成（Supabase 写入是同步的，但保险起见）
    time.sleep(0.05)
