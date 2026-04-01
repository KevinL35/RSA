"""
BERTopic 主题发现 HTTP 服务（与 scripts/dev.sh 分离，按需启动）。

仅从 Supabase 导出语料再跑挖掘（POST /discover-from-supabase）。

发现成功后默认将候选写入 Supabase `dictionary_review_queue`（词典审核待办）；可用
`auto_import_review_queue: false` 关闭，仍可用 JSONL + `run-bertopic-local.sh import-queue` 手动入队。

环境变量（可选）：
  BERTOPIC_API_KEY  — 若设置，则请求须带请求头 X-Bertopic-Api-Key: <值>
  SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY — 导出与入队所需
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field, model_validator

REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS = REPO_ROOT / "ml" / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import bertopic_review_queue_import_lib as rq  # noqa: E402
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
    auto_import_review_queue: bool = Field(
        True,
        description="非 dry_run 且存在候选时，自动写入 dictionary_review_queue（pending）",
    )
    dictionary_vertical_id: str = Field(
        "general",
        description="入队时的 dictionary_vertical_id",
    )
    skip_existing_pending: bool = Field(
        True,
        description="同一 batch_id+source_topic_id 已有 pending 时跳过，避免重复入队",
    )

    @model_validator(mode="after")
    def _insight_task_when_a_class(self) -> DiscoverFromSupabaseBody:
        if self.only_without_dimension_hits and not (self.insight_task_id or "").strip():
            raise ValueError("only_without_dimension_hits 为 true 时必须提供 insight_task_id")
        return self


class DiscoverFromUnmatchedPoolsBody(BaseModel):
    insight_task_id: str | None = Field(None, description="可选：仅处理某一任务")
    platform: str | None = None
    product_id: str | None = None
    limit_per_sentiment: int = Field(0, description="每个情感组导出上限，0 不限制")
    dry_run: bool = False
    use_local_configs: bool = False
    batch_end: str | None = None


def _topic_pool_table_by_sentiment(sentiment: str) -> str:
    if sentiment == "positive":
        return "topic_pool_highlight"
    if sentiment == "negative":
        return "topic_pool_pain"
    return "topic_pool_observation"


def _insert_topic_pool_rows(
    *,
    supabase_url: str,
    service_role_key: str,
    table_name: str,
    rows: list[dict],
) -> None:
    if not rows:
        return
    url = f"{supabase_url.rstrip('/')}/rest/v1/{table_name}"
    for r in rows:
        code, raw = rq.http_json(
            "POST",
            url,
            key=service_role_key,
            body=r,
            extra_headers={"Prefer": "return=minimal"},
        )
        if code not in (200, 201):
            raise HTTPException(status_code=502, detail=f"{table_name} 入库失败: HTTP {code}: {raw[:300]}")


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "bertopic-api"}


@app.post("/discover-from-supabase")
def post_discover_from_supabase(
    body: DiscoverFromSupabaseBody,
    _auth: None = Depends(_optional_api_key),
) -> dict:
    """
    从 Supabase 导出 reviews → BERTopic 挖掘。需环境变量 SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY。
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

        review_import: dict | None = None
        if (
            body.auto_import_review_queue
            and not body.dry_run
            and out.get("candidates")
        ):
            rq.load_platform_api_dotenv()
            base = (os.environ.get("SUPABASE_URL") or "").strip().rstrip("/")
            key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
            if not base or not key:
                raise HTTPException(
                    status_code=500,
                    detail="auto_import_review_queue 需要 SUPABASE_URL 与 SUPABASE_SERVICE_ROLE_KEY",
                )
            vid = (body.dictionary_vertical_id or "general").strip() or "general"
            payloads, warnings = rq.build_queue_payloads_from_candidate_rows(
                out["candidates"],
                vertical_id=vid,
                kind="new_discovery",
            )
            inserted, skipped, err = rq.import_payloads_to_dictionary_review_queue(
                payloads,
                skip_existing=body.skip_existing_pending,
                supabase_url=base,
                service_role_key=key,
            )
            if err:
                raise HTTPException(
                    status_code=502,
                    detail=f"词典审核队列入库失败：{err}",
                ) from None
            review_import = {
                "inserted": inserted,
                "skipped_pending": skipped,
                "parse_warnings": warnings[:50],
                "n_parse_warnings": len(warnings),
            }

        if review_import is not None:
            out = {**out, "review_queue_import": review_import}
        return out


@app.post("/discover-from-unmatched-pools")
def post_discover_from_unmatched_pools(
    body: DiscoverFromUnmatchedPoolsBody,
    _auth: None = Depends(_optional_api_key),
) -> dict:
    """从三分类未命中总表分组挖掘，并写入亮点池/痛点池/观察池。"""
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

    rq.load_platform_api_dotenv()
    base = (os.environ.get("SUPABASE_URL") or "").strip().rstrip("/")
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not base or not key:
        raise HTTPException(status_code=500, detail="缺少 SUPABASE_URL 或 SUPABASE_SERVICE_ROLE_KEY")

    run_batch_id = f"pool-{uuid.uuid4().hex[:12]}"
    sentiment_stats: dict[str, dict] = {}

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        for sentiment in ("positive", "negative", "neutral"):
            corpus_path = td_path / f"corpus_{sentiment}.csv"
            cmd: list[str] = [
                sys.executable,
                str(export_script),
                "--out",
                str(corpus_path),
                "--from-sentiment-unmatched",
                "--sentiment-label",
                sentiment,
            ]
            if body.insight_task_id:
                cmd.extend(["--insight-task-id", body.insight_task_id.strip()])
            if body.platform:
                cmd.extend(["--platform", body.platform])
            if body.product_id:
                cmd.extend(["--product-id", body.product_id])
            if body.limit_per_sentiment > 0:
                cmd.extend(["--limit", str(body.limit_per_sentiment)])

            try:
                subprocess.run(
                    cmd,
                    cwd=str(REPO_ROOT),
                    env=os.environ.copy(),
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except subprocess.CalledProcessError as e:
                tail = (e.stderr or e.stdout or str(e)).strip()
                raise HTTPException(status_code=502, detail=f"{sentiment} 导出失败：{tail}") from e

            if not corpus_path.is_file():
                sentiment_stats[sentiment] = {"n_candidates": 0, "pool_table": _topic_pool_table_by_sentiment(sentiment)}
                continue

            out = run_bertopic_discovery(
                corpus_csv=corpus_path,
                reports_dir=td_path,
                batch_strategy=bs,
                run_config=rc,
                batch_id=f"{run_batch_id}-{sentiment}",
                batch_end=body.batch_end,
                platform=body.platform,
                product_id=body.product_id,
                dry_run=body.dry_run,
                force=True,
            )

            pool_table = _topic_pool_table_by_sentiment(sentiment)
            rows: list[dict] = []
            for c in out.get("candidates") or []:
                rows.append(
                    {
                        "batch_id": run_batch_id,
                        "source_sentiment": sentiment,
                        "platform": str(c.get("platform") or ""),
                        "product_id": str(c.get("product_id") or ""),
                        "source_topic_id": str(c.get("source_topic_id") or ""),
                        "suggested_canonical": str(c.get("suggested_canonical") or ""),
                        "aliases": c.get("aliases") or [],
                        "quality_score": c.get("quality_score"),
                        "evidence_snippets": c.get("evidence_snippets") or [],
                    }
                )
            if not body.dry_run:
                _insert_topic_pool_rows(
                    supabase_url=base,
                    service_role_key=key,
                    table_name=pool_table,
                    rows=rows,
                )
            sentiment_stats[sentiment] = {
                "pool_table": pool_table,
                "n_candidates": len(rows),
            }

    return {
        "batch_id": run_batch_id,
        "dry_run": body.dry_run,
        "sentiments": sentiment_stats,
    }
