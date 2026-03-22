# integrations

外部依赖适配层（统一封装，避免业务代码直连第三方）：

- `supabase` 数据与认证底座
- `review_provider` 评论抓取 API（见 `app/integrations/review_provider/`，由 `POST .../fetch-reviews` 触发）
- `analysis_provider` 模型/大模型分析源（`POST .../insight-tasks/{id}/analyze`，见 `app/integrations/analysis_provider/`）
- `translation_provider` 翻译 API
- `agent_provider` 对比结论增强 API
