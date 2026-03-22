# Web 前端（Vue 3 + Vite）

业务入口：`src/app/`（路由、布局、菜单）；功能模块在 `src/modules/*`。

## 本地运行

```bash
npm install
npm run dev
```

环境变量见 **`.env.example`**。完整「要填什么」清单：**`docs/runbooks/env-to-run.md`**。

## 部署到 Vercel（或其它静态托管）

1. **构建**：在 **`apps/web`** 下 `npm ci && npm run build`，输出 **`dist`**；平台需配置 SPA **history fallback**（全部路径回退到 `index.html`）。
2. **环境变量**：`VITE_API_BASE_URL` = 线上 API 根地址（HTTPS、无尾斜杠）；后端 **CORS** 需允许前端域名。
3. 若不设 `VITE_API_BASE_URL`，浏览器会请求当前站点的 `/api/...`，需在托管平台为 **`/api` 单独配置反代**，否则易被 SPA 回退吞掉。生产更推荐显式设置 `VITE_API_BASE_URL`。
