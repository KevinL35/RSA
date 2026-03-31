# API Modules

与前端业务域对应的后端模块（实际代码所在目录）：

- `platform_users`：平台登录与账号权限（JWT、菜单键）
- `tasks`：洞察任务、抓取、分析、重试与任务列表
- `analysis_results`：分析结果查询与落库
- `insight_dashboard`：洞察结果页聚合（维度、痛点、证据）
- `dictionary`：词典与垂直类目

说明：鉴权与「接口配置」等能力已落在 `platform_users`、环境变量与独立路由中；历史上预留的仅占位空包已移除，避免与真实目录混淆。
