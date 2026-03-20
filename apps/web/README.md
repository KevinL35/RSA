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

## 迁移使用步骤

1. 将 `router/index.ts` 与你项目入口挂接（在 `main.ts` 中 `app.use(router)`）。
2. 将 `stores/auth.ts` 的 `login` 方法替换为真实登录 API。
3. 修改 `config/menu.config.ts` 为你的目标系统菜单。
4. 按菜单 path 在 `router/index.ts` 增加对应真实页面路由。
5. 将 `PlaceholderView.vue` 替换为实际业务页面组件。

## 备注

主题文案统一为“情感分析与痛点挖掘平台”，并保留左侧可收起菜单、右上退出登录、登录守卫。你可以在此基础上逐页替换业务实现。
