"""
BERTopic 主题发现 HTTP 服务（与 dev-all 分离，按需启动）。

环境变量（可选）：
  BERTOPIC_API_KEY  — 若设置，则请求须带请求头 X-Bertopic-Api-Key: <值>
  SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY — /discover-from-supabase 必需
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field, model_validator

REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS = REPO_ROOT / "ml" / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from run_bertopic_offline import run_bertopic_discovery  # noqa: E402

app = FastAPI(title="RSA BERTopic API", version="0.1.0")


def _optional_api_key(x_bertopic_api_key: str | None = Header(None, alias="X-Bertopic-Api-Key")) -> None:
    expected = (os.environ.get("BERTOPIC_API_KEY") or "").strip()
    if not expected:
        return
    if (x_bertopic_api_key or "").strip() != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Bertopic-Api-Key")


class DiscoverFromSupabaseBody(BaseModel):
    only_without_dimension_hits: bool = Field(
        False,
        description="True 时仅导出 A 类：有 review_analysis 且无 review_dimension_analysis 行",
    )
    insight_task_id: str | None = Field(
        None,
        description="A 类模式必填：洞察任务 UUID",
    )
    platform: str | None = None
    product_id: str | None = None
    limit: int = Field(0, description="导出上限，0 不限制")
    dry_run: bool = False
    use_local_configs: bool = Field(
        False,
        description="True 时使用 bertopic_*_local.yaml（小语料联调）",
    )
    batch_end: str | None = Field(None, description="YYYY-MM-DD UTC 窗口右边界，默认今天")

    @model_validator(mode="after")
    def _insight_task_when_a_class(self) -> DiscoverFromSupabaseBody:
        if self.only_without_dimension_hits and not (self.insight_task_id or "").strip():
            raise ValueError("only_without_dimension_hits 为 true 时必须提供 insight_task_id")
        return self


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "bertopic-api"}


@app.post("/discover")
def post_discover(
    corpus: UploadFile = File(..., description="TA-8 语料 CSV（含 text_en、platform、product_id 等）"),
    dry_run: bool = Form(False),
    use_local_configs: bool = Form(False),
    batch_end: str | None = Form(None),
    platform: str | None = Form(None),
    product_id: str | None = Form(None),
    _auth: None = Depends(_optional_api_key),
) -> dict:
    """
    上传 CSV 跑 BERTopic；结果写入临时目录并在响应中返回 manifest + candidates（大语料时注意响应体积）。
    """
    bs = (
        REPO_ROOT / "ml/configs/bertopic_batch_strategy_local.yaml"
        if use_local_configs
        else REPO_ROOT / "ml/configs/bertopic_batch_strategy_v1.yaml"
    )
    rc = (
        REPO_ROOT / "ml/configs/bertopic_run_local.yaml"
        if use_local_configs
        else REPO_ROOT / "ml/configs/bertopic_run_v1.yaml"
    )

    suffix = Path(corpus.filename or "corpus.csv").suffix or ".csv"
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        corp_path = td_path / f"corpus{suffix}"
        corp_path.write_bytes(corpus.file.read())

        try:
            out = run_bertopic_discovery(
                corpus_csv=corp_path,
                reports_dir=td_path,
                batch_strategy=bs,
                run_config=rc,
                batch_end=batch_end,
                platform=platform,
                product_id=product_id,
                dry_run=dry_run,
                force=True,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except FileExistsError as e:
            raise HTTPException(status_code=409, detail=str(e)) from e

        return out


@app.post("/discover-from-supabase")
def post_discover_from_supabase(
    body: DiscoverFromSupabaseBody,
    _auth: None = Depends(_optional_api_key),
) -> dict:
    """
    从 Supabase 导出 reviews → 同 POST /discover 逻辑。需环境变量 SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY。
    """
    bs = (
        REPO_ROOT / "ml/configs/bertopic_batch_strategy_local.yaml"
        if body.use_local_configs
        else REPO_ROOT / "ml/configs/bertopic_batch_strategy_v1.yaml"
    )
    rc = (
        REPO_ROOT / "ml/configs/bertopic_run_local.yaml"
        if body.use_local_configs
        else REPO_ROOT / "ml/configs/bertopic_run_v1.yaml"
    )

    export_script = REPO_ROOT / "ml" / "scripts" / "export_reviews_corpus_for_bertopic.py"
    if not export_script.is_file():
        raise HTTPException(status_code=500, detail="缺少 export_reviews_corpus_for_bertopic.py")

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        corp_path = td_path / "corpus_from_supabase.csv"

        cmd: list[str] = [
            sys.executable,
            str(export_script),
            "--out",
            str(corp_path),
        ]
        if body.only_without_dimension_hits:
            cmd.extend(
                [
                    "--insight-task-id",
                    (body.insight_task_id or "").strip(),
                    "--only-without-dimension-hits",
                ]
            )
        if body.platform:
            cmd.extend(["--platform", body.platform])
        if body.product_id:
            cmd.extend(["--product-id", body.product_id])
        if body.limit > 0:
            cmd.extend(["--limit", str(body.limit)])

        env = os.environ.copy()
        try:
            subprocess.run(
                cmd,
                cwd=str(REPO_ROOT),
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            tail = (e.stderr or e.stdout or str(e)).strip()
            raise HTTPException(status_code=502, detail=f"导出 Supabase 失败：{tail}") from e

        if not corp_path.is_file():
            raise HTTPException(status_code=502, detail="导出未生成 CSV 文件")

        try:
            out = run_bertopic_discovery(
                corpus_csv=corp_path,
                reports_dir=td_path,
                batch_strategy=bs,
                run_config=rc,
                batch_end=body.batch_end,
                platform=body.platform,
                product_id=body.product_id,
                dry_run=body.dry_run,
                force=True,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        return out
