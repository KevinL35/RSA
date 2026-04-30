# RSA 平台

一个面向评论洞察与词典治理的本地开发项目，包含前端页面、平台 API、分析 API 与 DeepSeek 适配层。

## 项目结构

- `frontend/web`：前端应用（Vite + Vue）
- `backend/platform-api`：平台后端 API（用户权限、词典、主题审核等）
- `backend/platform-api/analysis-engine`：分析相关能力服务（已并入 platform-api 目录）
- `backend/deepseek-adapter`：DeepSeek 适配服务
- `scripts/dev.sh`：本地一键启动脚本

## 命名映射（代码标识名 vs 业务名称）

为避免前后端、路由、权限和菜单文案出现歧义，项目统一采用“代码标识稳定、业务名称可迭代”的约定。

- `smart-mining` / `smartMining`：智能挖掘（当前标准标识）
- `dictionary`：词典管理
- `insight`：评论洞察
- `api-config` / `apiConfig`：系统设置
- `account-permissions` / `accountPermissions`：用户权限
- `audit-log` / `auditLog`：操作日志

说明：

- 代码中的 key（路由、权限、menu key、接口字段）以现有标识为准。
- 页面展示文案（如“智能挖掘”）通过 i18n 维护，不直接修改底层 key。
- 新增模块时，优先新增“映射说明”再开发，避免同义命名并存。

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
