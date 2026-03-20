# RSA 全局项目结构

基于 `docs` 的产品边界与阶段规划，项目统一按“业务域 + 技术层”组织。

## 顶层目录职责

- `apps/web`：前端应用（Vue 3 + TypeScript）
- `apps/api`：后端应用（FastAPI，业务编排与统一 API）
- `ml`：模型与离线流程（已归并原 `finetune`）
- `packages/contracts`：前后端共享契约（类型/OpenAPI）
- `infra`：部署、环境、迁移、CI
- `ops`：压测、监控、告警、运行手册
- `docs`：PRD / Spec / Plan / Task（需求真源）

## web 结构（已落地）

- `src/app`：应用壳（路由、守卫、全局 provider）
- `src/modules`：按业务域拆分（auth/insight/compare/tasks/settings/governance）
- `src/shared`：跨模块复用能力（services/components/i18n/types/utils）

## api 结构（已落地骨架）

- `app/core`：配置、日志、异常、权限中间件
- `app/modules`：按业务域拆分接口与服务
- `app/integrations`：第三方适配（supabase、抓评、分析、翻译、agent）
- `app/worker`：异步任务执行与重试

## 落地原则

1. 前端不直连业务数据库，统一通过 `apps/api`。
2. `supabase` 作为数据与认证底座，接入入口在 `apps/api/app/integrations`。
3. 接口变更先更新 `packages/contracts`，再改前后端实现。
