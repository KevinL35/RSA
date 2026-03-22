# contracts

前后端共享的 **API 数据契约**：用 TypeScript 描述请求体、响应体与领域模型，减少联调时字段不一致；长期可与 **OpenAPI** 对齐，由规范生成或校验类型。

## 目录结构

```
packages/contracts/
├── README.md                 # 本说明
├── openapi/                  # OpenAPI 规范与版本记录（预留）
│   └── README.md
└── src/
    ├── index.ts              # 统一导出入口
    ├── analysis.ts           # 情感 / 六维分析、落库结构
    ├── compare.ts            # 对比分析接口形状
    ├── insight-dashboard.ts  # 洞察结果页看板、证据与痛点排行
    ├── insight-tasks.ts      # 洞察任务 CRUD、列表、快照
    ├── reviews.ts            # 评论抓取结果、导出用行
    └── task-center.ts        # 任务中心列表、筛选、重试
```

新增接口契约时：**优先在对应域文件内定义类型**，并在 `index.ts` 中 `export type { ... }`，保持单点维护。

## 通用约定

- **`ApiEnvelope<T>`**（`index.ts`）：统一响应外壳 `{ code, message, data: T }`，与 `apps/api` 实际 JSON  envelope 保持一致；具体路径与 HTTP 方法以 FastAPI 路由为准。
- 命名以 **业务语义** 为主（如 `InsightTaskRow`、`DimensionAnalysis`），避免与框架类型混淆。

## 与 OpenAPI 的关系

- 当前类型多为 **手写**，用于文档化与跨端对齐。
- **`openapi/`** 用于存放后端导出的 OpenAPI 文档（如 `openapi.yaml`），目标能力包括：
  - 前端或脚本 **从 schema 生成 TypeScript**；
  - 联调 **冻结协议**、做 **版本 diff**。
- 迁移建议：接口变更时 **先更新契约**（手写或 OpenAPI 二选一作为真源），再改 `apps/api` 与 `apps/web` 实现；若生成类型落地，可让生成结果替换或补充 `src/`。

## 如何在应用中使用

仓库若尚未把本目录声明为 workspace 包，可在各应用中：

- **复制路径引用**：在 `tsconfig` 中配置 `paths` 指向 `packages/contracts/src`，或
- **后续**：在 monorepo 根增加 `package.json` workspaces，将 `contracts` 发布为内部包（如 `@rsa/contracts`），由 `apps/web`、`apps/api` 依赖。

无论哪种方式，原则不变：**接口形状以本目录（或由此生成的类型）为协商基准。**

## 维护清单（改接口时）

1. 修改或新增 `src/*.ts` 中的类型，并更新 `index.ts` 导出。
2. 同步修改 `apps/api` 路由 / Pydantic 模型与 `apps/web` 的 API 调用与展示类型（若尚未共用本包，两处类型需人工对齐）。
3. 若已启用 OpenAPI：更新 `openapi/` 下规范并重新生成类型（如有流水线）。

## 相关文档

- 产品文档与命名规则见 **`docs/README.md`**；应用与工程目录见 **`apps/`**、**`packages/`**、**`ml/`**、**`infra/`** 等及各目录内 README。`packages/contracts` 为前后端共享的 API 类型契约层。
