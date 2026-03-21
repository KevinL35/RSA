# 情感分析与痛点挖掘平台骨架（可迁移）

该目录提供一个最小可用骨架，包含：

- 登录页
- 左右布局（左菜单 + 右内容）
- 左侧菜单收起/展开
- 右上角退出登录
- 菜单配置化（支持自定义菜单名 + SVG）

## 目录说明

- `config/menu.config.ts`：菜单配置入口（迁移时主要修改此文件）
- `stores/auth.ts`：登录态管理（示例使用 localStorage）
- `router/index.ts`：路由和登录守卫
- `layouts/MainLayout.vue`：主界面骨架
- `views/LoginView.vue`：登录页面
- `views/DashboardView.vue`：首页示例
- `views/PlaceholderView.vue`：业务页面占位

## 本地运行（已接好入口）

```bash
npm install
npm run dev
```

## 部署到 Vercel

对纯静态 Vue 应用来说，Vercel 通常比自建 Nginx **更省事**（HTTPS、CDN、按分支预览）。注意：**API 仍在你的 FastAPI 上**，要在 Vercel 里把「前端怎么访问 API」定好。

1. **新建项目**：Import 本 Git 仓库，在 Vercel 项目设置里把 **Root Directory** 设为 `apps/web`（本仓库是 monorepo）。
2. **构建**：Build Command 默认 `npm run build`，Output Directory 默认 `dist` 即可。
3. **环境变量（构建期）**：在 Vercel → Settings → Environment Variables 增加 `VITE_API_BASE_URL`，值为你的线上 API 根地址（**不要**末尾斜杠），例如 `https://api.your-domain.com`。重新部署后生效。  
   - 前端请求会发到该地址下的 `/api/v1/...`，后端需配置 **CORS** 允许你的 `*.vercel.app`（及正式域名）。
4. **不推荐在 Vercel 上不填 `VITE_API_BASE_URL`**：未设置时请求会发到当前域名的 `/api/...`，而下面 `vercel.json` 会把未命中静态文件的路径都回退到 `index.html`，**容易把 API 请求也吃掉**。更稳妥的做法是：**生产环境始终设置 `VITE_API_BASE_URL`**，并在后端配好 CORS。若你坚持同源代理 `/api`，请在 `vercel.json` 的 `rewrites` **最前面**增加一条 `/api/:path*` → 真实后端的规则，再保留 SPA 回退。
5. **`vercel.json`**：为 `vue-router` **history 模式**提供 **SPA 回退**（刷新子路径时不 404）。

## 迁移使用步骤

1. 将 `router/index.ts` 与你项目入口挂接（在 `main.ts` 中 `app.use(router)`）。
2. 将 `stores/auth.ts` 的 `login` 方法替换为真实登录 API。
3. 修改 `config/menu.config.ts` 为你的目标系统菜单。
4. 按菜单 path 在 `router/index.ts` 增加对应真实页面路由。
5. 将 `PlaceholderView.vue` 替换为实际业务页面组件。

## 备注

主题文案统一为“情感分析与痛点挖掘平台”，并保留左侧可收起菜单、右上退出登录、登录守卫。你可以在此基础上逐页替换业务实现。
