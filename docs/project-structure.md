# 项目结构说明（归档）

该文档用于承接原先分散在源码目录下的占位 README，避免源码目录噪音，同时保留结构说明。

## 前端结构（frontend/web/src）

### app

应用壳层（不放业务逻辑）：

- 入口装配（router/pinia/i18n/provider）
- 全局布局与页面壳
- 全局守卫与初始化流程

### modules

按业务域拆分页面与状态：

- `auth`
- `insight`
- `tasks`
- `settings`
- `governance`

### shared

跨模块复用能力：

- `services` API 客户端与请求封装
- `ui` 通用 UI 适配与行为
- `utils` 工具函数
- `types` 公共类型（按需扩展）

## 后端结构（backend/platform-api/app）

### modules

与前端业务域对应的后端模块（实际代码目录）：

- `platform_users`：平台登录与账号权限
- `tasks`：洞察任务、抓取、分析、重试与任务列表
- `analysis_results`：分析结果查询与落库
- `insight_dashboard`：洞察结果页聚合（维度、痛点、证据）
- `dictionary`：词典与垂直类目
- `audit_log`：审计日志

### integrations

外部依赖适配层（统一封装，避免业务代码直连第三方）：

- `supabase`：数据与认证底座
- `review_provider`：评论抓取 API 适配
- `analysis_provider`：分析源适配
- `agent_enrichment`：增强能力适配

### worker

异步任务执行能力目前主要落在 `tasks` 相关模块中（如主题挖掘任务调度、重试与状态跟踪）。
