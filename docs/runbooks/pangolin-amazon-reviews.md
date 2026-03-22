# Pangolin（Pangolinfo）Amazon 评论 API 对接 TB-2

官方文档：[Amazon Review API](https://docs.pangolinfo.com/cn-api-reference/amazonReviewAPI/amazonReviewAPI)、[API 对接说明](https://docs.pangolinfo.com/cn-index)。

## 1. 获取 Token

按文档使用：

`POST https://scrapeapi.pangolinfo.com/api/v1/auth`  

Body：`{ "email", "password" }`  

响应 `code === 0` 时，**`data` 字段**即为长期有效的 Bearer Token（勿提交 Git）。

## 2. RSA 配置（`apps/platform-api/.env`）

```env
REVIEW_PROVIDER_MOCK=false
REVIEW_PROVIDER_MODE=pangolin
PANGOLIN_TOKEN=<上一步的 data 字符串>

# 与文档中 scrape 请求的 url 一致；抓美国站默认即可
PANGOLIN_AMAZON_URL=https://www.amazon.com
# 英国站示例：https://www.amazon.co.uk

# 默认约 10 条/页时可设 10 以接近 100 条；积点与耗时随页数增加
PANGOLIN_PAGE_COUNT=10
PANGOLIN_FILTER_BY_STAR=all_stars
PANGOLIN_SORT_BY=recent
PANGOLIN_PARSER_NAME=amzReviewV2
PANGOLIN_TIMEOUT_SECONDS=180
```

- **`PANGOLIN_PAGE_COUNT`**：列表页数；Amazon 常见约每页 10 条评论，**设为 10 约可拉 100 条**（以实际返回为准）。文档说明与积点消耗相关（如每页 N 积点），请按账户额度谨慎增大。
- 修改 `.env` 后**重启** API 进程。

## 3. 任务侧约定

- 洞察任务 `platform` 须为 **`amazon`**，`product_id` 为 **ASIN**（10 位）。
- 与 Apify 模式相同：通过 `POST /api/v1/insight-tasks/{id}/fetch-reviews` 触发。

## 4. 实现说明

- 代码：`apps/platform-api/app/integrations/review_provider/pangolin.py`
- 将返回中 `data.json[].data.results[]` 的 `content`、`reviewId`、`title`、`star`、`date` 等映射为内部 `reviews` 行。

## 5. 与 `http` / `apify` 的关系

三者互斥，由 `REVIEW_PROVIDER_MODE` 选择；`pangolin` 模式下**不需要**配置 `REVIEW_PROVIDER_URL`。
