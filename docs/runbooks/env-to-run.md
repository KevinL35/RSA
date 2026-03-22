# 要填什么才能跑起来

最小集合：**Supabase + 本地 API + 本地前端**。其它变量可按功能再开。

---

## 1. 后端 `apps/platform-api/.env`（在 `apps/platform-api/` 下自行新建）

| 变量 | 是否必填 | 说明 |
|------|----------|------|
| **`SUPABASE_URL`** | **必填** | Supabase Dashboard → **Project Settings → API → Project URL**，形如 `https://xxxxx.supabase.co`。**不要**填 anon/service 的 JWT。 |
| **`SUPABASE_SERVICE_ROLE_KEY`** | **必填** | 同一页里的 **service_role** secret（仅后端持有）。 |
| **`CORS_ORIGINS`** | 本地建议填 | 默认含 `http://localhost:5173`；若前端用别的端口或线上前端域名，用英文逗号追加。 |

**数据库**：在 Supabase **SQL Editor** 执行 `infra/migrations/` 下 `001`、`002`、`003`（见 `apps/platform-api/README.md`）。

**可选（有功能再配）**：

- `REVIEW_PROVIDER_*`、`ANALYSIS_PROVIDER_*`：抓评 / 分析外接 API；无真实源时可 `REVIEW_PROVIDER_MOCK=true`。接 Pangolinfo：**`REVIEW_PROVIDER_MODE=pangolin`** + `PANGOLIN_TOKEN` 等（`docs/runbooks/pangolin-amazon-reviews.md`）。或 **`REVIEW_PROVIDER_MODE=http`** + 任意实现 TB-2 `POST /fetch` 契约的 HTTP 服务。
- `TRANSLATION_API_*`：中文界面下的译文；不配则只显示英文分析文案。

启动：

```bash
cd apps/platform-api && source .venv/bin/activate  # 先 python -m venv .venv && pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 2. 前端 `apps/web/.env.local`（自行新建，勿提交 Git）

| 变量 | 是否必填 | 说明 |
|------|----------|------|
| **`VITE_API_BASE_URL`** | 本地建议填 | 本机 API：`http://127.0.0.1:8000`（无尾斜杠）。不填则走 Vite 代理 `/api` → `127.0.0.1:8000`。 |

启动：

```bash
cd apps/web && npm install && npm run dev
```

---

## 3. 仅部署前端（静态托管）

- **构建**：在 `apps/web` 执行 `npm ci && npm run build`，产物为 `apps/web/dist`。若平台支持 monorepo，可将 **Root Directory** 设为 `apps/web`，或在根目录用自定义 **Install / Build** 命令指向该目录。
- **SPA 路由**：需将任意路径 **回写到 `index.html`**（各平台称 rewrites / fallback，依文档配置）。
- **Production** 环境变量：**`VITE_API_BASE_URL`** = 你的 HTTPS API 根地址；后端 **`CORS_ORIGINS`** 需包含该前端域名。

---

## 4. 登录与角色

当前为演示登录：浏览器 **localStorage** 里的 `rsa_user_role`（`admin` / `operator` / `readonly`）。创建任务、抓评、分析需要 **operator 或 admin**。
