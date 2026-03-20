# RSA API（FastAPI）

业务编排层，**真实读写 Supabase（Postgres）**，不再返回占位 mock。

## 环境

1. 复制 `apps/api/.env.example` 为 `apps/api/.env`
2. 填入 `SUPABASE_URL`、`SUPABASE_SERVICE_ROLE_KEY`（使用 **service_role**，仅后端持有，勿提交前端）

## 数据库

在 Supabase SQL Editor 执行：

- `infra/migrations/001_insight_tasks.sql`

## 安装与启动

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 接口

- `GET /api/v1/insight-tasks`：列表（来自表 `insight_tasks`）
- `POST /api/v1/insight-tasks`：创建一条 `pending` 任务（用于联调）

前端开发：在 `apps/web` 运行 `npm run dev`，Vite 会将 `/api` 代理到 `http://127.0.0.1:8000`。

## 安全说明

当前接口未接 JWT 校验；上线前应在 `app/core` 中校验 Supabase 用户令牌，并与 RBAC 对齐。
