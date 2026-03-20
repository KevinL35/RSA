# TA-2 训练数据契约（Stage A）

## 文档信息

- 项目：电商评论情感与痛点分析系统
- 对应任务：`TA-2`
- 版本：`v1.0`
- 状态：`frozen`
- 对齐配置：
  - `finetune/configs/data_contract.yaml`
  - `finetune/configs/train_roberta.yaml`

## 1. 目标

定义 Stage A 统一训练数据契约，确保导入、清洗、切分、训练脚本使用同一字段与口径。

## 2. 数据层级与文件路径

### 2.1 文件路径（当前版本）

- 原始输入：`finetune/data/raw/reviews.csv`
- 清洗输出：`finetune/data/processed/reviews_cleaned.csv`
- 切分输出：
  - `finetune/data/splits/train.csv`
  - `finetune/data/splits/val.csv`
  - `finetune/data/splits/test.csv`

### 2.2 切分规则（冻结）

- `train = 0.8`
- `val = 0.1`
- `test = 0.1`
- `random_seed = 42`
- 分层切分字段：`label_sentiment`

## 3. 统一字段规范（最小集）

`reviews.csv` / `reviews_cleaned.csv` 必需字段：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 评论唯一 ID（建议稳定可复现） |
| `platform` | string | 是 | 站点/来源平台标识 |
| `product_id` | string | 是 | 商品标识（如 `asin`） |
| `raw_text` | string | 是 | 原始评论文本（保留追溯） |
| `analysis_input_en` | string | 是 | 模型输入文本（英文） |
| `lang` | string | 是 | 原文语种（如 `en`） |
| `created_at` | int64 | 是 | 时间戳（Unix 秒） |
| `source` | string | 是 | 数据来源标识 |
| `label_sentiment` | int | 是 | 情感标签（0/1/2） |

## 4. 标签契约

`label_sentiment` 仅允许如下值：

- `0` -> `negative`
- `1` -> `neutral`
- `2` -> `positive`

评分映射（导入阶段）：

- `<=2` -> `0`
- `=3` -> `1`
- `>=4` -> `2`

## 5. 清洗规则（冻结）

依据 `data_contract.yaml`：

- 文本非空：`analysis_input_en.strip() != ""`
- 长度范围：`5 <= len(analysis_input_en) <= 1024`
- 去重键：`id`

说明：

- 大文件默认支持分块清洗，避免一次性读入导致内存不足。
- 清洗后仅保留满足规则的数据行。

## 6. 训练输入契约（RoBERTa）

来自 `train_roberta.yaml`：

- 文本列：`analysis_input_en`
- 标签列：`label_sentiment`
- 模型：`roberta-base`
- `num_labels = 3`
- `max_length = 256`

训练产物与评估输出：

- 模型目录：`finetune/artifacts/roberta-sentiment-v0`
- 评估报告：`finetune/reports/sentiment_eval_v0.json`

## 7. 校验清单（执行前）

在运行切分和训练前，需满足：

- 必填字段齐全且拼写一致
- `label_sentiment` 仅包含 `{0,1,2}`
- `analysis_input_en` 无空串
- `id` 在清洗后不重复
- 样本量与类别分布可用于分层切分

## 8. 兼容性与变更策略

- 若接入新数据源（如 JSONL、CSV、API），必须先映射到本契约再入清洗流程。
- 增加字段不影响兼容；删除或改名必填字段属于破坏性变更，需要升版本并同步更新脚本。
- 推荐版本号：`ta2-vX.Y.Z`。

