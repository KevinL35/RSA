# 电商评论情感与痛点分析系统 - Task Breakdown (v1)

> 基于 `docs/prd/ecommerce-review-insights-v1-prd.md`、`docs/specs/ecommerce-review-insights-v1-spec.md` 与 `docs/plans/ecommerce-review-insights-v1-plan.md`（v1.2 起含**毕设周次 W0–W5**与论文章节，见该文档「毕业论文专项」）  
> 本文件只管**可执行拆解（TA/TB）**；学期节奏不对在此处重复维护。  
> 当前状态：**Stage B 执行中**（**TA-12a/b** 生产候选基线已在任务表闭合；M1 闭环 TB-1～TB-8；**TB-9～TB-14** 对比、i18n、RBAC 与回归测试已交付；TB-15 起按 M3 推进）

## Task Rules

- 优先级：P0 > P1 > P2
- 状态流转：`todo -> doing -> review -> done`
- 每个任务必须附带“完成定义（DoD）”
- 本文全部任务当前默认状态为 `todo`

### Stage A 和「先清洗、再微调」怎么对应

编号 **TA-1～TA-12** 是**工作包清单**，不是唯一步骤 1→12 的单一流水线。和你直觉最一致的一条主链是：

1. **TA-1 → TA-2**（短）：先定**情感标签、字段、切分规则**。不先定口径，清洗时容易删错列或标签对不齐；这两步一般是**文档 + 约定**，不代替写清洗代码。
2. **TA-3**：**数据集清洗与质检**（去重、去噪、长度、语言等）——这就是你说的「先把数据弄干净」。
3. **TA-4**：在清洗后的数据上**构造 RoBERTa 训练集**（`text_en` + `label_sentiment`）并 **train/val/test 切分**。
4. **TA-5**：在 TA-4 产物上做 **RoBERTa 微调与评估**（本计划是**在预训练 RoBERTa 上做分类微调**，不是从零训练整模大模型）。
5. **TA-6～TA-7**：六维词典 + **归因引擎**（规则/匹配，与情感模型是两条能力，常在 TA-5 跑通后与之 **拼成一条推理链**；词典种子可提早起草，与 TA-4/5 **部分并行**）。
6. **TA-8～TA-10**：BERTopic **离线**发现 + **词典回灌**（语料通常也用已清洗的 `analysis_input_en`，可与 TA-5 后段并行）。
7. **TA-11～TA-12**：推理 API **封装**与**版本基线**。

**结论**：**清洗 = TA-3，微调 = TA-5**；前面的 TA-1/TA-2 是微调与清洗的「规矩」，避免返工。若你已有干净且带情感标注的数据，TA-3 工作量会下降，但 **TA-2 契约仍建议保留**，保证和 plan/spec 一致。

---

## Stage A - 模型微调与评估（先行）

- **TA-1 冻结标签与评估口径**（P0，status: done）  
  - DoD：明确情感标签集合、六维定义、证据句与 `highlight_spans` 约定、RoBERTa/归因规则与词典/BERTopic 分别对应的评估指标。
- **TA-2 定义训练数据契约（字段/格式/版本）**（P0，status: done）  
  - DoD：输出统一数据字段规范（含 `raw_text` / `analysis_input_en`）与 split 规则（train/val/test）。
- **TA-3 数据清洗与质检流水线**（P0，status: review）  
  - DoD：实现去重、去噪、长度过滤、语言识别、标签一致性抽检，输出清洗报告。
- **TA-4 准备 RoBERTa 情感数据集并切分**（P0，status: review）  
  - DoD：生成可训练数据文件，类别分布可视化，类别失衡策略明确。
- **TA-5 RoBERTa 总体情感微调与评估（HuggingFace）**（P0）  
  - DoD：情感准确率 >= 85%；输出正/中/负标签与置信度，评估报告可复现。
- **TA-6 六维词典种子与归因匹配规则冻结**（P0，status: done）  
  - DoD：词条含 `dimension_6way`、别名、权重/优先级；匹配规则（长词优先、大小写/词形策略）与多命中冲突处理文档化；BERTopic 主题→词典字段格式约定。
- **TA-7 归因引擎实现与抽检评估**（P0，status: done）  
  - DoD：对 `analysis_input_en` 产出六维标签、痛点关键词、证据片段（`raw_text` 可追溯）、`highlight_spans`；抽检集上证据可追溯率与冲突处理结果可复现。
- **TA-8 准备 BERTopic 离线语料与批次策略**（P0，status: done）  
  - DoD：确定离线跑批频率、最小样本量、语料窗口与输入字段。  
  - 交付：`docs/stage-a/ecommerce-review-insights-v1-ta8-bertopic-corpus-batch-strategy.md`；`ml/configs/bertopic_batch_strategy_v1.yaml`；`ml/README.md` 索引更新。
- **TA-9 BERTopic 离线新痛点发现流程**（P0，status: done）  
  - DoD：可按批次产出主题候选词，包含主题质量评分与人工复核输入。  
  - 交付：`ml/scripts/run_bertopic_offline.py` + `bertopic_offline_lib.py`；`ml/configs/bertopic_run_v1.yaml`；`ml/requirements-bertopic.txt`；`docs/stage-a/ecommerce-review-insights-v1-ta9-bertopic-offline-discovery.md`；`ml/fixtures/bertopic_corpus_sample.csv`；`ml/tests/test_bertopic_offline_lib.py`。
- **TA-10 词典回灌机制（含版本化）**（P0，status: done）  
  - DoD：支持“候选词 -> 人工复核 -> 词典发布/回滚”，并记录版本与操作日志。  
  - 交付：`ml/scripts/taxonomy_backfill_lib.py`、`publish_taxonomy_backfill.py`、`rollback_taxonomy_overlay.py`；`ml/fixtures/taxonomy/`（灌库用 YAML）；`docs/stage-a/ecommerce-review-insights-v1-ta10-taxonomy-backfill.md`；`ml/fixtures/taxonomy_decisions_sample.jsonl`；`ml/tests/test_taxonomy_backfill_lib.py`；API `taxonomy_yaml` 合并 general overlay；分析服务按 `dictionary_vertical_id` 合并词典并文档更新。
- **TA-11 封装推理服务与统一协议**（P0，status: done）  
  - DoD：RoBERTa 情感 + 六维归因引擎（词典/规则）在线链路提供统一请求/响应契约，可作为 `analysis_provider_id` 被调用。  
  - 交付：`apps/analysis-api`（`POST /analyze`；可选 `SENTIMENT_MODEL_DIR` 加载微调权重；否则星级+启发式）；联调说明见 `apps/analysis-api/README.md` 与 `apps/platform-api/.env.example`。
- **TA-12a 模型版本临时基线发布（无回灌）**（P0，status: done）  
  - DoD：形成可追踪版本号、评估报告与发布说明（明确“未接入 BERTopic 回灌”），供 Stage B 先行接入与联调。  
  - 交付（已闭合）：**可追踪版本**以 Supabase `taxonomy_entries` 与灌库样例 `ml/fixtures/taxonomy/taxonomy_dictionary_seed_v1.yaml` 的 `version` / `taxonomy_id`（当前 `1.0.0` / `taxonomy-seed-v1`）及分析服务部署镜像/提交为准。**发布说明**：`apps/analysis-api/README.md`、`apps/platform-api/.env.example`（分析源 URL、`analysis_provider_id` 契约）。**Stage B 联调形态**：情感层可为占位/星级启发式或可选 `SENTIMENT_MODEL_DIR` 权重，不依赖 BERTopic 批次产物即可跑通洞察/落库/看板（与 DoD「无回灌」语义一致：联调基线不绑定离线主题回灌）。**专项准确率报告**仍以 **TA-5** 独立交付为准，不阻塞本基线作为产品化生产入口。
- **TA-12b 模型版本正式基线发布（含回灌）**（P0，status: done）  
  - DoD：在 TA-8～TA-10 完成后，形成可追踪版本号、评估报告、回灌记录与发布说明，作为 Stage B 生产候选基线。  
  - 交付（已闭合）：在 TA-8～TA-10 **done** 前提下，**回灌路径**为 `docs/stage-a/ecommerce-review-insights-v1-ta10-taxonomy-backfill.md` + `ml/scripts/publish_taxonomy_backfill.py` / `rollback_taxonomy_overlay.py` + `ml/fixtures/taxonomy_decisions_sample.jsonl`；**线上治理闭环**含词典 overlay 合并（`apps/platform-api` `taxonomy_yaml`）、分析服务按 `dictionary_vertical_id` 合并词典（`apps/analysis-api`）、Web 词典审核/管理/API `approve-entry` 与审计。**发布说明**：同 TA-12a 另附 TA-10 文档。**生产基线认定**：当前仓库 Stage B P0 主链（TB-1～TB-14）与上述词典/分析契约一并冻结为 v1 生产候选；RoBERTa 离线评估报告仍归 **TA-5** 补齐。

## Stage B - 前后端产品化（后续）

### Phase 1 - 基础链路（M1）

- **TB-1 建立洞察任务模型与状态机**（P0，status: done）  
  - DoD：支持 `pending/running/success/failed`；可查询任务状态与错误信息。  
  - 交付：`insight_tasks` 表（迁移已应用 Supabase）+ `GET`/`POST`/`PATCH`；状态机含 `cancelled`、`failed→pending`；错误字段 `error_code` / `error_message` / `failure_stage`。
- **TB-2 接入评论抓取 API 适配器**（P0，status: done）  
  - DoD：输入 `platform + product_id` 可拉取评论并落库；失败可重试并记录错误码。  
  - 交付：`reviews` 表 + `review_provider`（HTTP + 可配置重试 + `REVIEW_PROVIDER_MOCK` 联调）；`POST /api/v1/insight-tasks/{id}/fetch-reviews`；失败时任务 `failed` 且 `failure_stage=fetch` 与结构化 `error_code`。
- **TB-3 接入分析源调用链路（对接 Stage A 模型）**（P0，status: done）  
  - DoD：支持 `analysis_provider_id` 显式选择与默认回退；返回情感/六维/证据句结构。  
  - 交付：`POST /api/v1/insight-tasks/{id}/analyze`；`analysis_provider` 适配层；分析响应与前端/落库字段约定一致；分析成功后结果写入 TB-4 表。
- **TB-4 设计并落地分析结果存储结构**（P0，status: done）  
  - DoD：可按商品、任务、维度检索；证据句可反查原评论。  
  - 交付：表 `review_analysis`、`review_dimension_analysis`（迁移 `003_review_analysis.sql`）；`analyze` 成功路径落库；`GET /api/v1/insight-tasks/{id}/analysis`；`GET /api/v1/analysis/by-product`（可选 `dimension`）；`review_id` 联接 `reviews.raw_text`。
- **TB-5 洞察页查询接口（最小可用）**（P0，status: done）  
  - DoD：可查询痛点排行、维度聚合、证据句列表；空态和错误态明确。  
  - 交付：`GET /api/v1/insight-tasks/{id}/dashboard`（`dimension_counts`、`pain_ranking`、`evidence` 分页）；`TASK_NOT_READY` / `NO_ANALYSIS_DATA` 等 `empty_state`。
- **TB-6 任务中心后端接口（任务查询/重试）**（P0，status: done）  
  - DoD：支持按类型/状态/时间筛选任务；失败任务返回结构化错误；重试接口幂等。  
  - 交付：`GET /api/v1/insight-tasks` 查询参数 + `error` 块；`POST .../retry`（`failed→pending`，`pending` no-op）；单条 `GET`/`PATCH` 返回亦含 `error` 字段。
- **TB-7 任务中心前端页面（列表/状态/失败原因）**（P0，status: done）  
  - DoD：页面可查看任务状态、耗时、失败原因并触发重试；RBAC 权限生效。  
  - 交付：`TaskCenterPage` 筛选（状态、创建时间范围、limit）、状态标签、耗时、失败阶段/错误码/文案、`POST .../retry`；登录选择角色；侧边栏+路由 `allowedRoles`（管理员全量菜单，运营/只读隐藏系统设置与治理菜单；只读禁用重试）。
- **TB-8 P0 单测/集成测试（洞察+任务中心链路）**（P0，status: done）  
  - DoD：核心流程测试通过；关键失败路径（抓评失败/分析失败）可复现并被断言。  
  - 交付：`apps/platform-api/pytest.ini` + `tests/`（状态机、`error` 增强、dashboard 空态、重试 API 409/成功重置）；`pytest` 绿。

## Phase 2 - 对比、翻译、权限（M2）

- **TB-9 对比分析聚合接口**（P0，status: done）  
  - DoD：输出情感分布差异、六维差异、关键词差异、结论卡片。  
  - 交付：`GET /api/v1/compare/products`（按两商品各自**最近一次成功**洞察任务聚合 `review_analysis` / `review_dimension_analysis`）；Web `compare/types.ts` 与接口对齐；`tests/test_compare_service.py`。
- **TB-10 对比前置校验与引导**（P0，status: done）  
  - DoD：任一商品缺失分析数据时，返回可读提示并引导先做洞察。  
  - 交付：区分 `no_success_task` 与 `empty_analysis`；400 `detail` 含双语 `messages`/`guidance`/`next_step`；`apps/platform-api/app/modules/compare/guidance.py`；`tests/test_compare_guidance.py`；Web `compare/api.ts` + 对比页展示引导；类型与 `ComparePrerequisiteErrorDetail` 等在前端契约中维护。
- **TB-11 翻译展示策略实现**（P0，status: done）  
  - DoD：UI 非 English 时展示英文+译文；证据句始终原文；未配翻译 API 时不阻断。  
  - 交付：`POST /api/v1/translate`（LibreTranslate 兼容 JSON；未配置 `TRANSLATION_API_URL` 时 `configured=false`）；`translateApi.ts` + `BilingualBlock.vue`；对比结论在中文界面下英文主文+可选译文+机器翻译提示；证据句说明文案；`apps/platform-api/.env.example`。
- **TB-12 双语 UI 文案覆盖（en/zh-CN）**（P0，status: done）  
  - DoD：所有新增用户可见文案均提供 en 与 zh-CN。  
  - 交付：`vue-i18n` + `app/i18n/locales/en.ts` & `zh-CN.ts`；登录/侧栏/任务中心/对比/洞察/治理占位/设置演示表；`ElConfigProvider` 对齐 Element Plus 语言；`localStorage rsa_locale`。
- **TB-13 固定模板 RBAC（管理员/运营/只读）**（P0，status: done）  
  - DoD：前后端权限一致；越权访问被拒绝并可审计。  
  - 交付：请求头 `X-RSA-Role`（`admin`|`operator`|`readonly`）；变更类接口 `require_mutator_role`；`rsa.audit` 记录 403；前端 `api.ts` / 登录角色选择；与菜单、任务重试能力对齐。
- **TB-14 权限回归测试**（P0，status: done）  
  - DoD：3 角色关键路径与负路径（越权）测试通过。  
  - 交付：`apps/platform-api/tests/test_rbac.py`（401/403/operator/admin 正路径）；`apps/web` `npm run test`（`api.test.ts` 角色头契约）；既有 `test_retry_router` 已带 mutator 头。

## Phase 3 - 稳定性与上线准备（M3）

- **TB-15 洞察任务性能压测**（P0）  
  - DoD：1000 条评论任务 P95 <= 180s，成功率 >= 99%。
- **TB-16 对比接口性能压测**（P0）  
  - DoD：接口 P95 <= 2s，P99 <= 3s。
- **TB-17 并发与吞吐压测**（P0）  
  - DoD：并发洞察任务 5、查询 QPS 20 达标。
- **TB-18 可观测性与告警**（P0）  
  - DoD：监控看板覆盖 SLA/成功率/可用性，具备基础告警规则。
- **TB-19 上线回归与发布清单**（P0）  
  - DoD：关键业务回归通过，发布回滚路径明确。

## Optional P1（是否纳入待你确认）

- **TB-20 SKU 维度分布与对比**（P1）  
  - DoD：存在 SKU 数据时可筛选/聚合；无 SKU 时空态正确。
- **TB-21 导出增强（异步导出）**（P1）  
  - DoD：支持明细/汇总导出；大数据量异步任务可追踪。
- **TB-22 痛点审核菜单（管理员）**（P1）  
  - DoD：可查看候选主题（关键词/证据句/频次/质量分）并执行通过/驳回/暂缓，操作可追溯。
- **TB-23 词典管理菜单（版本发布/回滚）**（P1）  
  - DoD：可查看生效版本与词条来源；支持发布新版本与回滚；权限受 RBAC 约束。

## Open Blocking Items

- **B0 Stage A 临时基线质量门槛是否通过（TA-12a）**（阻塞：高）→ **已闭合**（见 TA-12a 交付）  
- **B0.1 RoBERTa/六维词典归因/BERTopic 回灌是否达成正式闭环验收（TA-12b）**（阻塞：高）→ **已闭合**（词典归因 + BERTopic→回灌→审核写 overlay 链路见 TA-12b；**RoBERTa 微调指标与独立评估报告**仍以 **TA-5** 为准）  
- **B1 痛点评分公式是否配置化**（阻塞：中）  
- **B2 六维关键词标准化词表首版最小范围**（阻塞：中）  
- **B3 首批上线站点优先级确认**（阻塞：低）
- **B4 痛点审核与词典管理上线节奏（v1.1 全开或灰度）**（阻塞：低）

## 已知优化项与后续补齐（技术债）

> 下列项**不否定**当前 Stage B 生产候选基线（TA-12）的可用性，但作为**模型与词典质量**的持续改进清单，与 **TA-5 / TA-6 / TA-8～TA-9** 对齐记录。


| 优先级建议  | 项                            | 现状                                           | 后续方向                                                                                                                                                                                                                  |
| ------ | ---------------------------- | -------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 中～高    | **RoBERTa 情感微调（TA-5）**       | 训练集仅使用约 **一成** 数据做过训练，**不能**代表全量数据上的最终指标与泛化。 | 在固定 train/val/test 切分下逐步扩比例至全量（或团队约定比例）；补可复现 **评估报告**（准确率/宏平均等）后再将 TA-5 标为完成。                                                                                                                                         |
| 高      | **六维词典（TA-6 + overlay）**     | 词条与别名 **尚未完善**，归因与痛点展示会受覆盖度与歧义影响。            | 优先高频、低歧义 canonical；日常迭代走 **overlay** 与词典审核；规则变更同步库内种子/样例 YAML 的 `version`/`taxonomy_id` 与 TA-6 文档。                                                                                             |
| 中（可并行） | **BERTopic 离线发现（TA-8～TA-9）** | 对流程与参数 **熟悉度不足**。                            | 先读 `docs/stage-a/ecommerce-review-insights-v1-ta9-bertopic-offline-discovery.md`、`ml/configs/bertopic_run_v1.yaml`，用 `ml/fixtures/bertopic_corpus_sample.csv` 跑通 `run_bertopic_offline.py`；产出候选再经人工与 **TA-10** 回灌进词典。 |


## 执行建议（供你决策）

- 方案 A（阶段化最稳妥）：先完整执行 Stage A，再执行 Stage B 的全部 P0。
- 方案 B（平衡）：Stage A + Stage B 全部 P0，**按需纳入 TB-20（SKU）**；导出增强与词典治理菜单（TB-22/23）延后。
- 方案 C（全量）：Stage A + Stage B 全部 P0 + P1 同步推进（含痛点审核/词典管理）。

---

**Task Version**: 1.2.3（在 1.2.2 基础上增「已知优化项与后续补齐」小节：RoBERTa 一成训练、六维词典待完善、BERTopic 熟悉度）  
**Status**: Review Required  
**Execution**: Stage A：**TA-12a/b 生产候选基线已认领完成**（见上交付）。Stage B：M1（TB-1～TB-8）与 M2（TB-9～TB-14）已交付；M3（TB-15～TB-19）仍待执行