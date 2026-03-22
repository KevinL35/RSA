# RSA API（FastAPI）

业务编排层，**真实读写 Supabase（Postgres）**。

**环境变量清单（最小必填项）**：见 `docs/runbooks/env-to-run.md`。

## 环境

1. 复制 `apps/api/.env.example` 为 `apps/api/.env`
2. 填入 `SUPABASE_URL`（**Project URL**，`https://…supabase.co`，勿填 JWT）、`SUPABASE_SERVICE_ROLE_KEY`（**service_role**，仅后端持有，勿提交前端）

## 数据库

在 **你的 Supabase 项目**打开 **SQL Editor**：可直接打开仓库内 **`infra/migrations/ALL_FOR_SQL_EDITOR.sql`**，**全选复制**（仅 SQL，不要复制 bash 命令）→ 粘贴 → **Run**。改迁移后请重生成该文件：`bash scripts/print-supabase-migrations.sh > infra/migrations/ALL_FOR_SQL_EDITOR.sql`。或仍可按文件逐个执行：

- `infra/migrations/001_insight_tasks.sql`
- `infra/migrations/002_reviews.sql`（TB-2 评论落库）
- `infra/migrations/003_review_analysis.sql`（TB-4 分析结果）
- `infra/migrations/004_insight_tasks_dictionary_vertical.sql`（如使用词典垂直）
- `infra/migrations/005_platform_users.sql`（平台登录用户与菜单权限；默认账号 `admin` / `admin`，bcrypt 存储）
- `infra/migrations/006_insight_tasks_created_by.sql`（洞察任务 `created_by` 创建人用户名；创建任务时由前端 `X-RSA-Username` 传入）
- `infra/migrations/007_compare_runs.sql`（对比分析历史，前端列表/结果走 `GET|POST|DELETE /api/v1/compare/runs`）

然后将该项目的 **Project URL** 与 **service_role** 密钥填入 `apps/api/.env`。

## 安装与启动

本地若要 **同时** 起 Model API、本 API 与前端，可在仓库根目录执行：`bash scripts/dev-all.sh`（见 `apps/rsa-model-api/README.md`）。

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

- `GET /api/v1/insight-tasks`：洞察任务列表（TB-6），支持 `task_type=insight`、`status`（逗号分隔）、`created_after` / `created_before`（ISO8601）、`limit`；**失败**任务每条含 `error: { stage, code, message }`
- `GET /api/v1/insight-tasks/{id}`：单条查询（状态与 `error_*` / `failure_stage`）
- `POST /api/v1/insight-tasks`：创建一条 `pending` 任务（用于联调）
- `PATCH /api/v1/insight-tasks/{id}`：状态迁移（TB-1 状态机：`pending→running→success|failed|cancelled`，`failed→pending` 重试）；迁到 `failed` 时须带 `failure_stage` 与 `error_message`
- `POST /api/v1/insight-tasks/{id}/fetch-reviews`：TB-2 按任务的 `platform`/`product_id` 调用配置的评论抓取 API，写入 `reviews`；成功则任务保持 `running`；失败则 `failed` 且 `failure_stage=fetch` 与 `error_code`
- `GET /api/v1/insight-tasks/{id}/reviews?limit=`：列出任务已落库评论（默认 `limit=5000`，最大 `20000`），供前端导出 Excel（`.xlsx`）等；只读角色可访问
- `POST /api/v1/insight-tasks/{id}/analyze`：TB-3 读取已落库 `reviews`，调用分析源（任务上的 `analysis_provider_id` 优先，否则 `ANALYSIS_PROVIDER_DEFAULT_ID`；URL 由 `ANALYSIS_PROVIDER_ROUTES_JSON` 或 `ANALYSIS_PROVIDER_URL` 解析）；返回逐条情感/六维/证据结构；**成功则先写入 TB-4 表再** `running→success`；失败则 `failed` 且 `failure_stage=analyze`
- `GET /api/v1/insight-tasks/{id}/analysis`：TB-4 按任务读取已落库分析结果，每条带 `review` 原文片段字段便于证据反查
- `GET /api/v1/analysis/by-product?platform=&product_id=`：TB-4 按商品拉取六维命中行（可选 `dimension=`），每项附带 `review` 原文
- `GET /api/v1/insight-tasks/{id}/dashboard`：TB-5 洞察聚合（`dimension_counts`、`pain_ranking` 关键词频次、`evidence` 分页）；`evidence_limit` / `evidence_offset` / `evidence_dimension`；未就绪时 `empty_state` 说明原因
- `POST /api/v1/insight-tasks/{id}/retry`：TB-6 **幂等**重试：`failed→pending` 并清空错误；已为 `pending` 则 `idempotent: true`；`running`/`success`/`cancelled` 返回 409
- `DELETE /api/v1/insight-tasks/{id}`：删除任务（`admin`/`operator`）；关联 `reviews` / `review_analysis` / `review_dimension_analysis` 随库级 `ON DELETE CASCADE` 清理；不存在返回 404
- `GET /api/v1/compare/products?platform_a=&product_id_a=&platform_b=&product_id_b=`：TB-9 双商品对比；按各自最近一次 `success` 任务聚合情感分布、`dimensions` 六维计数、关键词 Top 与相对偏多侧、`conclusion_cards`（规则模板）。**TB-10 前置校验**：任一侧无 `success` 任务、或任务成功但 `review_analysis` 为空（无落库分析）时 **400**，响应体 `{"detail": { ... }}` 内含 `code: MISSING_INSIGHT_DATA`、`messages.zh_CN` / `messages.en`、`guidance`、`next_step`（引导至评论洞察）、`reasons`（`no_success_task` | `empty_analysis`）、`products`（含 `insight_task_id`）

**评论抓取（TB-2）环境变量**（`apps/api/.env`）：

- `REVIEW_PROVIDER_MODE`：`http`（默认）、`apify` 或 `pangolin`
- **`http`**：`REVIEW_PROVIDER_URL` 为完整 `POST` URL，JSON body：`platform`, `product_id`；可选 `REVIEW_PROVIDER_API_KEY` → `Authorization: Bearer`；响应须为顶层数组或 `reviews`/`items`/`data`/`results`/`records`；元素字段兼容 `raw_text`/`text`/`body`/`content`/`reviewText` 等
- **`apify`**：内置调用 Apify `run-sync-get-dataset-items`，**无需** `REVIEW_PROVIDER_URL`；需 `APIFY_TOKEN`、`APIFY_ACTOR_ID`；可选 `APIFY_INPUT_STYLE`（`asins`|`productUrls`）、`APIFY_MAX_REVIEWS`、`APIFY_RUN_TIMEOUT_SECONDS`（≤300，同步接口上限）
- **`pangolin`**：[Pangolinfo Amazon Review API](https://docs.pangolinfo.com/cn-api-reference/amazonReviewAPI/amazonReviewAPI)：`POST …/api/v1/scrape`，需 `PANGOLIN_TOKEN`（`POST …/api/v1/auth` 返回的 `data`）；可选 `PANGOLIN_AMAZON_URL`（默认 `https://www.amazon.com`，英亚等可改域名）、`PANGOLIN_PAGE_COUNT`（每页扣费见对方文档）、`PANGOLIN_FILTER_BY_STAR`、`PANGOLIN_SORT_BY`、`PANGOLIN_PARSER_NAME`、`PANGOLIN_TIMEOUT_SECONDS`；详见 `docs/runbooks/pangolin-amazon-reviews.md`
- `REVIEW_PROVIDER_TIMEOUT_SECONDS`：`http` 模式下的客户端超时（秒）
- `REVIEW_FETCH_MAX_RETRIES`：默认 3（429/5xx 等可重试错误）
- `REVIEW_PROVIDER_MOCK=true`：不请求外网，返回两条占位评论

**线 A（外部分析源先跑通）**：见 `docs/runbooks/line-a-external-model-e2e.md`（与 `ANALYSIS_PROVIDER_*` / `REVIEW_PROVIDER_MOCK` 对齐步骤）。

**分析源（TB-3）环境变量**：

- `ANALYSIS_PROVIDER_URL`：默认分析 HTTP 端点（当路由表未命中某 `analysis_provider_id` 时回退到此 URL）
- `ANALYSIS_PROVIDER_DEFAULT_ID`：任务未带 `analysis_provider_id` 时使用的逻辑 id（默认 `default`）
- `ANALYSIS_PROVIDER_ROUTES_JSON`：可选，例 `{"default":"https://a/analyze","llm":"https://b/run"}`，按 id 选 URL
- `ANALYSIS_PROVIDER_API_KEY`：可选 Bearer
- `ANALYSIS_PROVIDER_TIMEOUT_SECONDS`：默认 120
- `ANALYSIS_MAX_RETRIES`：默认 2（429/5xx/超时等退避重试）
- `ANALYSIS_PROVIDER_MOCK=true`：不请求外网，返回占位情感+六维结果；**无需**配置 `ANALYSIS_PROVIDER_URL` / `ROUTES_JSON`
- **本地闭环（自建情感+词典归因）**：另起进程运行 `apps/rsa-model-api`（见该目录 `README.md`），并在 `ANALYSIS_PROVIDER_ROUTES_JSON` 中为前端默认的 `ins_builtin` 配置 `http://127.0.0.1:8089/analyze`（详见 `apps/api/.env.example` 注释）

**分析源请求体（本系统 POST）**：`insight_task_id`, `platform`, `product_id`, `analysis_provider_id`（解析后的生效 id）, `reviews`（`id`, `raw_text`, …）。

**分析源响应**：顶层数组或 `reviews`/`results`/`items` 数组；元素含 `review_id`、`sentiment`（`label` + `confidence`）、`dimensions`（`dimension` 为 TA-1 六维 key：`pros`|`cons`|`return_reasons`|`purchase_motivation`|`user_expectation`|`usage_scenario`，及 `keywords`、`evidence_quote`、`highlight_spans`）。未匹配行将补 `neutral` 与空维度。

**翻译代理（TB-11）环境变量**：

- `TRANSLATION_API_URL`：可选，LibreTranslate 兼容 `POST`（JSON：`q`, `source`, `target`, `format`），返回 JSON 含 `translatedText`（或 `translated`/`data` 字符串）
- `TRANSLATION_API_KEY`：可选 `Authorization: Bearer …`
- 未配置时：`POST /api/v1/translate` 仍返回 **200**，`{"configured":false,"translated":null}`，前端仅展示英文主文，不阻断

前端开发：在 `apps/web` 运行 `npm run dev`，Vite 会将 `/api` 代理到 `http://127.0.0.1:8000`。

## RBAC（TB-13）

所有 `/api/v1/**` 业务接口（除文档中另有说明外）需在 HTTP 头中携带：

- **`X-RSA-Role`**：`admin` | `operator` | `readonly`

- **只读（`readonly`）**：仅允许 **GET** 类查询（任务列表、单条任务、dashboard、analysis、compare、translate 等）。
- **变更（`admin` / `operator`）**：可 **POST**（创建任务、拉取评论、分析、重试）与 **PATCH** 任务。

缺少或非法角色返回 **401**；只读角色调用变更类接口返回 **403**，`detail.code=RBAC_FORBIDDEN`，并写入日志 `rsa.audit`（WARNING）。

前端 `apps/web` 从登录所选角色写入 `localStorage`（`rsa_user_role`），`fetch` 自动带 `X-RSA-Role`。

## 安全说明

当前为 **演示级** RBAC（请求头角色 + 审计日志），未接 JWT；上线前应改为签名校验（如 Supabase Auth JWT）并与 RBAC 对齐。
