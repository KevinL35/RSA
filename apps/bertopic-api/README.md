# BERTopic API（主题发现 HTTP 服务）

在本地以 HTTP 方式调用 `ml/scripts/run_bertopic_offline.py` 的 `run_bertopic_discovery`，用于上传 CSV 或从 Supabase 导出后再跑 BERTopic。**依赖较重**（`sentence-transformers`、`torch` 等），**未** 并入 `scripts/dev-all.sh`，请按需单独启动。

## 安装

在**仓库根目录**执行（`-r ../../ml/requirements-bertopic.txt` 相对本目录解析）：

```bash
cd apps/bertopic-api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 启动

```bash
cd apps/bertopic-api
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8090
```

健康检查：`GET http://127.0.0.1:8090/health`

## 鉴权（可选）

若设置环境变量 `BERTOPIC_API_KEY`，则所有 `POST` 请求须带请求头：

`X-Bertopic-Api-Key: <与环境变量一致>`

## 接口

- **`POST /discover`**：`multipart/form-data`，字段 `corpus`（CSV 文件）；可选 `dry_run`、`use_local_configs`、`batch_end`、`platform`、`product_id`。`use_local_configs=true` 时使用 `ml/configs/bertopic_*_local.yaml`。
- **`POST /discover-from-supabase`**：JSON 体。默认从 `public.reviews` 分页导出（可选 `platform`、`product_id`、`limit`）。若 `only_without_dimension_hits: true`，须同时提供 `insight_task_id`（与 `export_reviews_corpus_for_bertopic.py` A 类一致）。

需 **`SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`**（子进程会跑 `ml/scripts/export_reviews_corpus_for_bertopic.py`，该脚本也会尝试从 `apps/platform-api/.env` 补全变量）。

## 响应体积

成功时响应内含完整 `candidates` 列表；语料很大时 JSON 可能很大，必要时可在外层网关限流或改为只落盘再拉取（当前实现为单次 JSON 返回）。
