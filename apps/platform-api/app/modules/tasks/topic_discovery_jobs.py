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
    insight_task_id: UUID,
    embedding_model: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    job_id = str(uuid4())
    row = {
        "id": job_id,
        "insight_task_id": str(insight_task_id),
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
        args=(job_id, str(insight_task_id), embedding_model, dry_run),
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
    insight_task_id: str,
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
    cmd = [
        py,
        str(script),
        "--insight-task-id",
        insight_task_id,
        "--embedding-model",
        embedding_model,
    ]
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
