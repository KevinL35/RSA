"""子进程调用 ml/topic_mining/scripts/bertopic_supabase_pools.py，避免在 uvicorn 进程内加载 torch/bertopic。"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import UUID

# apps/platform-api/app/modules/tasks/topic_pools_job.py → 仓库根为 parents[5]
_REPO_ROOT = Path(__file__).resolve().parents[5]


def run_topic_pools_subprocess(
    insight_task_id: UUID,
    *,
    embedding_model: str,
    dry_run: bool = False,
    python_executable: str | None = None,
) -> dict:
    """
    返回 {"returncode": int, "stdout": str, "stderr": str, "summary": dict | None}
    """
    script = _REPO_ROOT / "ml" / "topic_mining" / "scripts" / "bertopic_supabase_pools.py"
    if not script.is_file():
        raise FileNotFoundError(f"未找到脚本: {script}")

    py = (python_executable or os.environ.get("TOPIC_MINING_PYTHON") or "").strip() or sys.executable
    cmd: list[str] = [
        py,
        str(script),
        "--insight-task-id",
        str(insight_task_id),
        "--embedding-model",
        embedding_model,
    ]
    if dry_run:
        cmd.append("--dry-run")

    proc = subprocess.run(
        cmd,
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=86400,
        env=os.environ.copy(),
    )
    summary: dict | None = None
    if proc.stdout.strip():
        try:
            # 脚本最后一行应为完整 JSON；若有多行日志，取最后一个 JSON 对象块
            raw = proc.stdout.strip().splitlines()
            for line in reversed(raw):
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    summary = json.loads(line)
                    break
            if summary is None:
                summary = json.loads(proc.stdout.strip())
        except (json.JSONDecodeError, ValueError):
            summary = None

    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "summary": summary,
    }
