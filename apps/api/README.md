# RSA API（FastAPI）

业务编排层，**真实读写 Supabase（Postgres）**，不再返回占位 mock。

## 环境

1. 复制 `apps/api/.env.example` 为 `apps/api/.env`
2. 填入 `SUPABASE_URL`、`SUPABASE_SERVICE_ROLE_KEY`（使用 **service_role**，仅后端持有，勿提交前端）

## 数据库

在 **你的 Supabase 项目**（任意区域，含新加坡）打开 **SQL Editor**，依次执行：

- `infra/migrations/001_insight_tasks.sql`
- `infra/migrations/002_reviews.sql`（TB-2 评论落库）
- `infra/migrations/003_review_analysis.sql`（TB-4 分析结果）

然后将该项目的 **Project URL** 与 **service_role** 密钥填入 `apps/api/.env`。

## 安装与启动

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 测试（TB-8）

```bash
cd apps/api
source .venv/bin/activate
pytest
```

## 接口

- `GET /api/v1/insight-tasks`：任务中心列表（TB-6），支持 `task_type=insight`、`status`（逗号分隔）、`created_after` / `created_before`（ISO8601）、`limit`；**失败**任务每条含 `error: { stage, code, message }`
- `GET /api/v1/insight-tasks/{id}`：单条查询（状态与 `error_*` / `failure_stage`）
- `POST /api/v1/insight-tasks`：创建一条 `pending` 任务（用于联调）
- `PATCH /api/v1/insight-tasks/{id}`：状态迁移（TB-1 状态机：`pending→running→success|failed|cancelled`，`failed→pending` 重试）；迁到 `failed` 时须带 `failure_stage` 与 `error_message`
- `POST /api/v1/insight-tasks/{id}/fetch-reviews`：TB-2 按任务的 `platform`/`product_id` 调用配置的评论抓取 API，写入 `reviews`；成功则任务保持 `running`；失败则 `failed` 且 `failure_stage=fetch` 与 `error_code`
- `POST /api/v1/insight-tasks/{id}/analyze`：TB-3 读取已落库 `reviews`，调用分析源（任务上的 `analysis_provider_id` 优先，否则 `ANALYSIS_PROVIDER_DEFAULT_ID`；URL 由 `ANALYSIS_PROVIDER_ROUTES_JSON` 或 `ANALYSIS_PROVIDER_URL` 解析）；返回逐条情感/六维/证据结构；**成功则先写入 TB-4 表再** `running→success`；失败则 `failed` 且 `failure_stage=analyze`
- `GET /api/v1/insight-tasks/{id}/analysis`：TB-4 按任务读取已落库分析结果，每条带 `review` 原文片段字段便于证据反查
- `GET /api/v1/analysis/by-product?platform=&product_id=`：TB-4 按商品拉取六维命中行（可选 `dimension=`），每项附带 `review` 原文
- `GET /api/v1/insight-tasks/{id}/dashboard`：TB-5 洞察聚合（`dimension_counts`、`pain_ranking` 关键词频次、`evidence` 分页）；`evidence_limit` / `evidence_offset` / `evidence_dimension`；未就绪时 `empty_state` 说明原因
- `POST /api/v1/insight-tasks/{id}/retry`：TB-6 **幂等**重试：`failed→pending` 并清空错误；已为 `pending` 则 `idempotent: true`；`running`/`success`/`cancelled` 返回 409

**评论抓取（TB-2）环境变量**（`apps/api/.env`）：

- `REVIEW_PROVIDER_URL`：第三方抓取接口完整 URL（`POST`，JSON body：`platform`, `product_id`；可配 `Authorization: Bearer`）
- `REVIEW_PROVIDER_API_KEY`：可选
- `REVIEW_PROVIDER_TIMEOUT_SECONDS`：默认 30
- `REVIEW_FETCH_MAX_RETRIES`：默认 3（429/5xx/超时/连接错误重试）
- `REVIEW_PROVIDER_MOCK=true`：无真实 API 时返回两条占位评论，便于联调

响应 JSON 支持顶层数组，或 `reviews` / `items` / `data` / `results` / `records` 数组；元素字段兼容 `raw_text`/`text`/`body`/`content`/`reviewText` 等。

**分析源（TB-3）环境变量**：

- `ANALYSIS_PROVIDER_URL`：默认分析 HTTP 端点（当路由表未命中某 `analysis_provider_id` 时回退到此 URL）
- `ANALYSIS_PROVIDER_DEFAULT_ID`：任务未带 `analysis_provider_id` 时使用的逻辑 id（默认 `default`）
- `ANALYSIS_PROVIDER_ROUTES_JSON`：可选，例 `{"default":"https://a/analyze","llm":"https://b/run"}`，按 id 选 URL
- `ANALYSIS_PROVIDER_API_KEY`：可选 Bearer
- `ANALYSIS_PROVIDER_TIMEOUT_SECONDS`：默认 120
- `ANALYSIS_MAX_RETRIES`：默认 2（429/5xx/超时等退避重试）
- `ANALYSIS_PROVIDER_MOCK=true`：不请求外网，返回占位情感+六维结果

**分析源请求体（本系统 POST）**：`insight_task_id`, `platform`, `product_id`, `analysis_provider_id`（解析后的生效 id）, `reviews`（`id`, `raw_text`, …）。

**分析源响应**：顶层数组或 `reviews`/`results`/`items` 数组；元素含 `review_id`、`sentiment`（`label` + `confidence`）、`dimensions`（`dimension` 为 TA-1 六维 key：`pros`|`cons`|`return_reasons`|`purchase_motivation`|`user_expectation`|`usage_scenario`，及 `keywords`、`evidence_quote`、`highlight_spans`）。未匹配行将补 `neutral` 与空维度。

前端开发：在 `apps/web` 运行 `npm run dev`，Vite 会将 `/api` 代理到 `http://127.0.0.1:8000`。

## 安全说明

当前接口未接 JWT 校验；上线前应在 `app/core` 中校验 Supabase 用户令牌，并与 RBAC 对齐。
