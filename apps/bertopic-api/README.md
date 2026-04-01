# BERTopic API（主题发现 HTTP 服务）

在本地以 HTTP 触发：从 **Supabase `public.reviews`** 导出语料，再调用 `run_bertopic_discovery`（实现位于 `ml/topic_mining/scripts/run_bertopic_offline.py`；若该脚本未安装，接口会返回 503）。**依赖较重**（`sentence-transformers`、`torch` 等），**未**并入 `scripts/dev.sh`，请按需单独启动。

**日常路径**：只使用本服务的 **`POST /discover-from-supabase`** + Supabase 环境变量；不再推荐本地 fixture/自定义 CSV 跑批。

**词典审核入队（默认开启）**：发现完成且 `dry_run` 为 false 时，会自动把 `candidates` 写入 `dictionary_review_queue`（与手动 `import-queue` 相同逻辑）。响应中会增加 `review_queue_import`：`inserted`、`skipped_pending`、`parse_warnings` 等。若需只拿 JSON 不入库，请求体设 **`auto_import_review_queue: false`**。

离线 `import-queue` 脚本已下线，请优先使用 `auto_import_review_queue=true` 自动入队。

## 安装

在**仓库根目录**执行（`-r ../../ml/requirements-bertopic.txt` 相对本目录解析）：

```bash
cd apps/bertopic-api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 启动

**推荐（仓库根目录）**：自动 `source apps/platform-api/.env`（若存在），再启动服务。

```bash
bash scripts/bertopic.sh
```

可选端口：`BERTOPIC_PORT=8091 bash scripts/bertopic.sh`

**手动**：

```bash
cd apps/bertopic-api
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8090
```

健康检查：`GET http://127.0.0.1:8090/health`

## 鉴权（可选）

若设置环境变量 `BERTOPIC_API_KEY`，则 `POST` 请求须带请求头：

`X-Bertopic-Api-Key: <与环境变量一致>`

## 接口

**`POST /discover-from-supabase`**：JSON 体。默认从 `public.reviews` 分页导出（可选 `platform`、`product_id`、`limit`）。若 `only_without_dimension_hits: true`，须同时提供 `insight_task_id`（与 `export_reviews_corpus_for_bertopic.py` A 类一致）。

需 **`SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`**（子进程会跑 `ml/topic_mining/scripts/export_reviews_corpus_for_bertopic.py`，该脚本也会尝试从 `apps/platform-api/.env` 补全变量）。

可选 JSON 字段：`dry_run`、`use_local_configs`、`batch_end`、`auto_import_review_queue`（默认 true）、`dictionary_vertical_id`（默认 `general`）、`skip_existing_pending`（默认 true）。

## 响应体积与后续步骤

成功时响应内含完整 `candidates` 列表（及 `manifest`、`batch_id` 等）；语料很大时 JSON 可能很大，必要时在外层网关限流或关闭 `auto_import_review_queue` 后自行分批入队。默认已自动写入 **`dictionary_review_queue`**（见上文）。
