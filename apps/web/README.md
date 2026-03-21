# Web 前端（Vue 3 + Vite）

业务入口：`src/app/`（路由、布局、菜单）；功能模块在 `src/modules/*`。

## 本地运行

```bash
npm install
npm run dev
```

环境变量见 **`.env.example`**。完整「要填什么」清单：**`docs/runbooks/env-to-run.md`**。

## 部署到 Vercel（monorepo）

仓库 **根目录** 已有 **`vercel.json`**（`install`/`build` 指向 `apps/web`，并含 SPA 回退）。Vercel 导入本仓库时 **Root Directory 保持仓库根** 即可与之一致。

1. **环境变量**：`VITE_API_BASE_URL` = 线上 API 根地址（HTTPS、无尾斜杠）；后端 **CORS** 需允许前端域名。
2. 若不设 `VITE_API_BASE_URL`，浏览器会请求当前站点的 `/api/...`，需在 Vercel **rewrites 最前**增加 `/api` 反代，否则易被 SPA 回退吞掉。生产更推荐显式设置 `VITE_API_BASE_URL`。
