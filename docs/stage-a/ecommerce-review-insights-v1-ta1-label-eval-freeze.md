# TA-1 冻结标签与评估口径（Stage A）

## 文档信息

- 项目：电商评论情感与痛点分析系统
- 对应任务：`TA-1`
- 版本：`v1.0`
- 状态：`frozen`
- 生效范围：Stage A（模型微调与评估）

## 1. 目标与边界

本文件用于冻结以下口径，避免后续 TA-3/TA-4/TA-5 返工：

- 情感标签集合与映射
- 六维定义（用于后续归因能力）
- 证据句与 `highlight_spans` 数据结构约定
- RoBERTa、归因规则/词典、BERTopic 的评估口径

本文件不包含具体代码实现细节（由 `finetune/scripts/` 与后续 TA 任务负责）。

## 2. 情感标签集合（冻结）

### 2.1 标签定义

- `0 = negative`：负向评价（通常对应 1~2 星）
- `1 = neutral`：中性评价（通常对应 3 星）
- `2 = positive`：正向评价（通常对应 4~5 星）

### 2.2 数据映射规则（弱监督）

- 输入评分字段：`overall` 或 `score`
- 映射规则：
  - `<= 2` -> `0`
  - `= 3` -> `1`
  - `>= 4` -> `2`

说明：该映射是电商评论常见弱监督方案，适用于 Stage A 快速建立可用基线。

## 3. 六维定义（冻结）

六维固定为：

1. `pros`（优点）
2. `cons`（缺点）
3. `return_reasons`（退货原因）
4. `purchase_motivation`（购买动机）
5. `user_expectation`（用户期望）
6. `usage_scenario`（应用场景）

说明：TA-1 只冻结维度定义；具体词条、规则优先级和冲突策略由 TA-6/TA-7 完成。

## 4. 证据句与高亮结构约定（冻结）

为支持可解释下钻，后续归因引擎输出需满足：

- `evidence_quote`：原始评论片段（来自 `raw_text`，不翻译）
- `highlight_spans`：命中词在 `evidence_quote` 内的字符区间数组

`highlight_spans` 结构：

```json
[
  {"start": 15, "end": 23, "label": "keyword"}
]
```

约束：

- `start` 为闭区间起点，`end` 为开区间终点
- 索引基于 UTF-8 解码后的 Python 字符串位置
- 证据必须可回溯到 `review_id`

## 5. 评估口径（冻结）

### 5.1 RoBERTa 总体情感（TA-5）

- 主指标：
  - `Accuracy`
  - `Macro-F1`
- 辅助指标：
  - `Confusion Matrix`
- 质量门槛：
  - `Accuracy >= 85%`（与 PRD 对齐）

### 5.2 六维归因规则 + 词典（TA-7）

- 词典命中率（抽样）
- 冲突处理一致性（规则复现）
- 证据可追溯率（可追溯到 `review_id` 的比例）

### 5.3 BERTopic 离线发现（TA-9/TA-10）

- 主题连贯性（coherence）
- 主题覆盖率（coverage）
- 候选词人工通过率（审核通过 / 候选总量）

## 6. 版本与变更规则

- 标签集合、六维定义、评估主指标属于冻结项，变更必须升版本并在本文件记录。
- 推荐版本号：`ta1-vX.Y.Z`。
- 本版本 `v1.0` 与以下配置保持一致：
  - `finetune/configs/data_contract.yaml`
  - `finetune/configs/train_roberta.yaml`

