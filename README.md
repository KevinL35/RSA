# RSA 平台

一个面向评论洞察与词典治理的本地开发项目，包含前端页面、平台 API、分析 API 与 DeepSeek 适配层。

## 项目结构

- `apps/web`：前端应用（Vite + Vue）
- `apps/platform-api`：平台后端 API（用户权限、词典、主题审核等）
- `apps/analysis-api`：分析相关 API
- `apps/deepseek-adapter`：DeepSeek 适配服务
- `scripts/dev.sh`：本地一键启动脚本

## 本地启动

在仓库根目录执行：

```bash
bash scripts/dev.sh
```

默认会启动：

- Analysis API：`http://127.0.0.1:8089`
- Platform API：`http://127.0.0.1:8000`
- DeepSeek Adapter：`http://127.0.0.1:9100`（可选）
- Web：终端输出的 Vite 地址

## 常用参数

- 跳过 DeepSeek 适配层：

```bash
SKIP_DEEPSEEK_ADAPTER=1 bash scripts/dev.sh
```

- 自定义端口：

```bash
ANALYSIS_PORT=8089 API_PORT=8000 ADAPTER_PORT=9100 bash scripts/dev.sh
```

## 说明

- 目前 `dev.sh` 已关闭默认自动迁移逻辑。
- 如需数据库迁移，请按项目约定手动执行。
