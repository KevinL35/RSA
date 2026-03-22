# Pangolin（Pangolinfo）Amazon 评论 API 对接 TB-2

官方文档：[Amazon Review API](https://docs.pangolinfo.com/cn-api-reference/amazonReviewAPI/amazonReviewAPI)、[API 对接说明](https://docs.pangolinfo.com/cn-index)。

## 1. 获取 Token

按文档使用：

`POST https://scrapeapi.pangolinfo.com/api/v1/auth`  

Body：`{ "email", "password" }`  

响应 `code === 0` 时，**`data` 字段**即为长期有效的 Bearer Token（勿提交 Git）。

## 2. RSA 配置（`apps/platform-api/.env`）

**抓取多少页 / 请求多大 `pageCount`：只改本机 `.env`，不要改代码。** 设置 `PANGOLIN_PAGE_COUNT`（及可选 `PANGOLIN_PAGE_COUNT_MAX`）后，`get_settings()` 每次抓取都会读到；模板见同目录 `apps/platform-api/env.example`。

```env
REVIEW_PROVIDER_MOCK=false
REVIEW_PROVIDER_MODE=pangolin
PANGOLIN_TOKEN=<上一步的 data 字符串>

# 与文档中 scrape 请求的 url 一致；抓美国站默认即可
PANGOLIN_AMAZON_URL=https://www.amazon.com
# 英国站示例：https://www.amazon.co.uk

# —— 抓取页数（仅此调整即可）——
PANGOLIN_PAGE_COUNT=10
PANGOLIN_PAGE_COUNT_MAX=100

PANGOLIN_FILTER_BY_STAR=all_stars
PANGOLIN_SORT_BY=recent
PANGOLIN_PARSER_NAME=amzReviewV2
PANGOLIN_TIMEOUT_SECONDS=180
```

- **`PANGOLIN_PAGE_COUNT`**：传给 Pangolin 的 `bizContext.pageCount`（从第 1 页起连续拉多少页）。代码侧会限制在 **1～`PANGOLIN_PAGE_COUNT_MAX`**（默认 **100**）。
- **Amazon / 抓取路径约 ~100 条上限（重要）**：商品评论在亚马逊前台本身往往只展示有限条数（常见观察约 **10 页 × ~10 条 ≈ 100 条**）；通过 Pangolin 等 scrape 通常也**无法在一次任务里突破该量级**。把 `PANGOLIN_PAGE_COUNT` 调到 50 仍只有 ~100 条时，属于 **数据源与站点规则**，不是 RSA 配置未生效。若业务需要全量历史评论，需另寻数据源或对方是否提供翻页/多任务方案（以 Pangolin 最新文档为准）。
- **条数为 99 等**：适配层会丢弃**无正文**的条目（空 `content`/`body`/`text`），故可能比上游 `results` 少 1～几条。
- **Mock**：`REVIEW_PROVIDER_MOCK=true` 时固定 **100 条** 假数据，与 Pangolin 无关。
- **`.env` 未加载**：当前已固定从 `apps/platform-api/.env` 绝对路径读取，与启动 cwd 无关；若仍异常再查环境变量是否覆盖。
- 修改 `.env` 后一般无需重启即可生效（`get_settings()` 每次新建）；改代码后需重启。

## 3. 任务侧约定

- 洞察任务 `platform` 须为 **`amazon`**，`product_id` 为 **ASIN**（10 位）。
- 通过 `POST /api/v1/insight-tasks/{id}/fetch-reviews` 触发（与 `http` 模式同一入口）。

## 4. 实现说明

- 代码：`apps/platform-api/app/integrations/review_provider/pangolin.py`
- 将返回中 `data.json[].data.results[]` 的 `content`、`reviewId`、`title`、`star`、`date` 等映射为内部 `reviews` 行。

## 5. 与 `http` 的关系

`pangolin` 与 `http` 由 `REVIEW_PROVIDER_MODE` 二选一；`pangolin` 模式下**不需要**配置 `REVIEW_PROVIDER_URL`。
