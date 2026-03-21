# 线 A：外部分析源端到端联调（微调未完成时）

目标：在 **RoBERTa/自研推理服务未就绪** 时，仍可用 **外部 HTTP 分析 API**（或 `ANALYSIS_PROVIDER_MOCK`）跑通：**创建任务 → 抓评论 → 分析落库 → Dashboard / 前端结果页**。

## 1. 环境与数据库

- `apps/api/.env`：`SUPABASE_*`、迁移 `001`～`003` 已执行（见 `apps/api/README.md`）。
- **评论**：无真实抓取 API 时设 `REVIEW_PROVIDER_MOCK=true` 便于联调；接 Apify：`REVIEW_PROVIDER_MODE=apify`（见 `docs/runbooks/apify-amazon-reviews.md`）；接 Pangolinfo：`REVIEW_PROVIDER_MODE=pangolin` 与 `PANGOLIN_TOKEN`（见 `docs/runbooks/pangolin-amazon-reviews.md`）。
- **分析源**（二选一或组合）：
  - **外部分析服务**：配置 `ANALYSIS_PROVIDER_URL`（单端点），或 `ANALYSIS_PROVIDER_ROUTES_JSON` 按 `analysis_provider_id` 路由多条 URL。
  - **快速冒烟**：`ANALYSIS_PROVIDER_MOCK=true`（不请求外网，返回占位六维）。

请求/响应格式见 `apps/api/README.md`「分析源请求体 / 响应」。

## 2. `analysis_provider_id` 与前端「接口配置」对齐

- 创建任务时可带 `analysis_provider_id`（见 `POST /api/v1/insight-tasks`）。
- 后端用该 id 在 `ANALYSIS_PROVIDER_ROUTES_JSON` 里查 URL；查不到则回退 `ANALYSIS_PROVIDER_URL`。
- **建议**：`ROUTES_JSON` 的 key 与前端 **洞察模型** 配置行的 `id`（如 `ins_builtin`、`cfg_xxx`）一致，这样从「添加商品」创建的任务会打到预期端点。

示例：

```env
ANALYSIS_PROVIDER_DEFAULT_ID=default
ANALYSIS_PROVIDER_ROUTES_JSON={"ins_builtin":"https://your-llm-gateway/v1/analyze","default":"https://your-llm-gateway/v1/analyze"}
```

## 3. 推荐调用顺序（单任务）

1. `POST /api/v1/insight-tasks`  
   Body：`{ "platform": "amazon", "product_id": "B0XXXXXXXXX", "analysis_provider_id": "ins_builtin" }`  
   Header：`X-RSA-Role: operator` 或 `admin`。
2. `POST /api/v1/insight-tasks/{id}/fetch-reviews`
3. `POST /api/v1/insight-tasks/{id}/analyze`
4. `GET /api/v1/insight-tasks/{id}/dashboard`（或打开前端结果页 `/insight-analysis/result/{id}`）

## 4. 前端线 A 行为（已实现）

- **评论洞察**列表：`GET /api/v1/insight-tasks` 拉取最近任务；失败时回退示例行并提示。
- **添加商品**：对每条链接解析 ASIN（或截断为 `product_id`）→ 创建任务 → 抓评 → 分析；需 **operator/admin** 角色。
- **查看结果**：成功任务跳转真实 `taskId`；仍可用 `demo` 看 UI 占位数据。

## 5. 常见问题

| 现象 | 排查 |
|------|------|
| `ANALYSIS_PROVIDER_NOT_CONFIGURED` | 未配置 `ANALYSIS_PROVIDER_URL` 且路由表无该 id。 |
| 分析 HTTP 4xx/5xx | 检查外服 URL、鉴权、请求体是否与 README 一致。 |
| 403 创建/抓评/分析 | 登录角色改为 **operator** 或 **admin**。 |
| Dashboard `NO_ANALYSIS_DATA` | 任务虽 success 但无维度落库；检查分析源返回的 `dimensions` 是否含 TA-1 六维 key。 |

## 6. 与 Stage A 的衔接

外部源跑通线 A 后，**TA-5～TA-11、TA-12a** 来自研服务替换同一 `analysis_provider_id` 对应 URL 或新增 key，无需改任务状态机与表结构。
