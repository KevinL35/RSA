# TA-9 BERTopic 离线新痛点发现流程（Stage A）

## 文档信息

- 项目：电商评论情感与痛点分析系统
- 对应任务：`TA-9`
- 版本：`v1.0`
- 状态：`frozen`
- 上游：`TA-8` 语料与批次策略；`TA-6` §5 候选 → 词典导入字段约定
- 下游：`TA-10` 人工复核与词典版本发布（见 `ecommerce-review-insights-v1-ta10-taxonomy-backfill.md`）

## 1. 目标与边界

在**离线**环境按批次对评论语料运行 BERTopic，为每条主题产出**候选痛点词条**（关键词、代表句、质量分），作为人工复核输入；**不**阻塞在线洞察链路，**不**自动写入生产词典。

## 2. 输入

- CSV（或可由导出脚本生成的同等列），列要求见 `docs/stage-a/ecommerce-review-insights-v1-ta8-bertopic-corpus-batch-strategy.md`。
- 机器默认：`ml/configs/bertopic_batch_strategy_v1.yaml`（窗口、最小样本、切片键）。
- 模型与聚类超参：`ml/configs/bertopic_run_v1.yaml`（嵌入模型、`min_topic_size`、`nr_topics` 等）。

## 3. 输出

在 `ml/reports/`（可用 `--reports-dir` 覆盖）生成：

| 文件 | 说明 |
|------|------|
| `bertopic_run_{batch_id}.json` | 批次元数据：`batch_end`、`window_days`、各切片文档数/主题数/离群数；`skipped` 记录未达标切片或运行异常 |
| `bertopic_candidates_{batch_id}.jsonl` | 每行一个候选主题，供审核与后续 TA-10 导入 |

### 3.1 JSONL 字段（人工复核输入）

| 字段 | 说明 |
|------|------|
| `batch_id` | 本次发现批次 |
| `platform` / `product_id` | 切片键 |
| `source_topic_id` | BERTopic 主题编号（批次内引用） |
| `suggested_canonical` | 由主题 top c-TF-IDF 词拼接的**建议**规范词（审核可改） |
| `aliases` | 额外高频词，便于审核写正式别名列表 |
| `quality_score` | `0–100` 启发式分数（见 §4） |
| `quality_components` | 可解释分量：文档数、top 词 c-TF-IDF、切片内最大主题规模等 |
| `evidence_snippets` | 代表评论句（优先 `get_representative_docs`，否则回退为该主题内前几条文本） |
| `dimension_6way` | 默认 `null`，**须由审核人**按 TA-1 六维择一后再走词典回灌 |
| `reviewer_notes` | 默认 `null`，供审核备注 |

与 `ml/fixtures/taxonomy/taxonomy_dictionary_seed_v1.yaml` 中 `bertopic_candidate_import` 对齐：`suggested_canonical`、`dimension_6way`（审核后）、`source_topic_id`、`batch_id` 为导入必填；其余为可选增强字段。

## 4. 主题质量评分（v1）

本阶段**不强制**计算学术 Coherence（如 NPMI）；采用可运维的 **proxy**：

- **规模项**：主题文档数相对本切片最大主题规模的比例。
- **区分度项**：c-TF-IDF 排名第一项的分数（相对经验上限做截断）。

合成 `quality_score` 仅用于**排序与优先审核**，不作为自动通过/驳回依据。

## 5. 命令示例

在**仓库根目录**执行（需先安装 BERTopic 依赖）：

```bash
pip install -r ml/requirements-bertopic.txt
python ml/scripts/run_bertopic_offline.py \
  --corpus-csv path/to/export.csv \
  --batch-end 2025-03-01
```

常用选项：

- `--dry-run`：只统计切片与 `skipped`，不加载模型。
- `--platform` / `--product-id`：只跑单一商品切片。
- `--batch-id`：固定批次 ID；否则自动生成。
- `--force`：覆盖已存在的同 `batch_id` 报告文件。

## 6. 与评估口径（TA-1）的关系

- **主题连贯性 / 覆盖率 / 人工通过率**：在 TA-9 产出稳定后，由离线评测与审核台账统计；本脚本提供可追溯的 `batch_id` 与 `quality_score` 辅助台账。

## 7. 版本与变更

- 变更默认超参：升 `bertopic_run_v1.yaml` 的 `version` 并记录于批次 manifest。
- 变更候选 JSONL 契约：同步 `TA-6` YAML 中 `bertopic_candidate_import` 与本文档，并协调 `TA-10` 导入脚本。
