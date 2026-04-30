# Web 前端（Vue 3 + Vite）

业务入口：`src/app/`（路由、布局、菜单）；功能模块在 `src/modules/*`。

## 本地运行

```bash
npm install
npm run dev
```

可选：在 `frontend/web/` 新建 **`.env.local`**（勿提交 Git）。完整「要填什么」清单：**`docs/runbooks/env-to-run.md`**。

## 部署（静态托管）

1. **构建**：在 **`frontend/web`** 下 `npm ci && npm run build`，输出 **`dist`**；托管平台需配置 SPA **history fallback**（未匹配路径回退到 `index.html`）。
2. **环境变量**：`VITE_API_BASE_URL` = 线上 **Platform API** 根地址（HTTPS、无尾斜杠）；后端 **`CORS_ORIGINS`** 需包含前端来源域名。
3. 若不设 `VITE_API_BASE_URL`，浏览器会向当前站点请求 `/api/...`，需在网关为 **`/api` 配置反代** 到 Platform API，否则易被 SPA 回退吞掉。生产环境建议显式设置 `VITE_API_BASE_URL`。
