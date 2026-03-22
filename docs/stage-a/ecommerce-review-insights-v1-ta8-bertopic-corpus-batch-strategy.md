# TA-8 BERTopic 离线语料与批次策略（Stage A）

## 文档信息

- 项目：电商评论情感与痛点分析系统
- 对应任务：`TA-8`
- 版本：`v1.0`
- 状态：`frozen`
- 对齐配置：`ml/configs/bertopic_batch_strategy_v1.yaml`
- 上游依赖：`TA-2` 字段契约、`TA-3` 清洗规则（语料须为**已清洗**评论）
- 下游消费：`TA-9` 离线主题发现（见 `ecommerce-review-insights-v1-ta9-bertopic-offline-discovery.md`）、`TA-10` 词典回灌（`batch_id`、窗口与样本量需与运行记录一致）

## 1. 目标

冻结 BERTopic **离线**跑批所用的语料范围、调度节奏与最小规模门槛，保证各批次可复现、可审计，并与 `docs/plans/ecommerce-review-insights-v1-plan.md` 中「BERTopic 语料字段」一致。

## 2. 语料输入字段（冻结）

BERTopic **仅对英文分析句**做主题建模；批次元数据用于切片与追溯。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `text_en` | string | 是 | 与 `TA-2` 的 `analysis_input_en` **同源同值**（清洗后、非空、长度满足清洗契约） |
| `platform` | string | 是 | 站点/平台标识，与线上一致 |
| `product_id` | string | 是 | 商品标识（如 ASIN）；**单批次默认按「platform + product_id」切片** |
| `created_at` | int64 | 是 | 评论时间 Unix **秒**（UTC）；用于语料窗口过滤 |
| `id` | string | 否 | 评论唯一 ID（即 TA-2 的 `id`）；**强烈建议纳入导出**，便于候选证据回链 `reviews` |

不要求情感标注、六维标注。

### 2.1 与线上一致性

- 从数仓/API 导出时：优先使用与洞察链路相同的清洗产物或同等规则，避免「离线主题」与「在线归因」基于不同文本形态。
- `text_en` 禁止混用 `raw_text`（原文可能非英文，且与证据句展示口径不一致）。

## 3. 语料时间窗口（冻结）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `window_days` | `90` | 滚动窗口：包含满足 `created_at >= batch_end - window_days` 且 `created_at < batch_end` 的评论 |
| `batch_end` | 跑批日 00:00:00 UTC | 每次运行的窗口右边界（写入 `topic_discovery_runs` 的批次元数据） |

可调策略（需在运行记录中写明，不视为默认）：

- 季节性品类可临时使用 `window_days: 180`。
- 新品冷启动：若 90 天内评论过少，允许**仅本次**扩大窗口至 `180`，仍受「最小样本量」约束（见第 4 节）。

## 4. 最小样本量（冻结）

BERTopic 在**过短语料**上主题不稳定，以下为**默认门槛**（与 `bertopic_batch_strategy_v1.yaml` 一致）。

| 切片粒度 | 最小文档数 | 未达标时的行为 |
|----------|------------|----------------|
| `platform` + `product_id`（默认） | `200` | **跳过该切片**，记录 `skipped_insufficient_n`；不产出空主题糊弄下游 |
| 平台级聚合（可选，多 `product_id` 合并为一跑） | `800` | 仅用于探索性批次，须在 `batch_id` 元数据中标记 `slice_mode: platform_wide` |

文档计数规则：

- 与 TA-3 一致：去重键为 `id`（若缺 `id` 则退化为 `text_en` + `created_at` 组合键，**不推荐**）。
- 仅统计 `text_en` 非空且长度 ∈ `[5, 1024]` 的行（与 `ml/configs/data_contract.yaml` 清洗上下界对齐）。

## 5. 离线跑批频率（冻结）

| 模式 | 默认节奏 | 适用说明 |
|------|----------|----------|
| 计划批 | **每周一次**（建议固定 UTC 日，如周一 02:00） | 常规词典迭代与监控主题漂移 |
| 低频 | **每月一次** | 评论量极低的长尾商品，避免重复空跑 |
| 临时批 | **按需触发** | 大促后、改版后、运营显式申请；仍使用同一窗口与字段口径 |

约束：

- BERTopic **不参与**在线实时分析链路；跑批失败**不阻塞**评论洞察任务（与 PRD/spec 一致）。
- 同一 `(platform, product_id, batch_end, window_days)` 在 24h 内重复提交视为**幂等重试**，不重复落库候选（由 `TA-9` 实现时保证）。

## 6. 批次标识与可复现性

每次运行须生成：

- `batch_id`：全局唯一字符串（建议 UUID 或 `topic-pipeline-v{semver}-{YYYYMMDD}-{short_hash}`）。
- 记录：`window_days`、`batch_end`、`min_documents`、`slice_mode`、`corpus_schema_version`（默认 `ta8-v1`）、输入行数与过滤后行数。

## 7. 校验清单（执行前）

- 导出列包含至少 `text_en`, `platform`, `product_id`, `created_at`。
- `created_at` 时区约定为 UTC，与库表一致。
- 单切片 `n >= min_documents` 再调用 BERTopic；否则按第 4 节跳过并记日志。
- 变更默认窗口、最小样本或频率时：升版本 `ta8-vX.Y.Z`，并同步更新 `bertopic_batch_strategy_v1.yaml` 与本文档「文档信息」版本行。

## 8. 版本与变更策略

- 默认策略以 `ml/configs/bertopic_batch_strategy_v1.yaml` 为机器可读真源；本文件为说明与审计依据。
- 破坏性变更（字段改名、默认窗口/门槛调整）需同步 `TA-9`/`TA-10` 脚本与 `topic_discovery_runs` 字段说明。
