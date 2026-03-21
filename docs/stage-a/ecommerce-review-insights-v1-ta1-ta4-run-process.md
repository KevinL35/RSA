# TA-1 到 TA-4 运行过程说明（论文可引用）

## 1. 阶段目标

Stage A 前半段（TA-1~TA-4）的目标是先构建可复现的数据与实验基线，为 TA-5 的 RoBERTa 微调提供稳定输入。执行顺序为：

`TA-1 标签与评估口径冻结 -> TA-2 数据契约冻结 -> TA-3 数据清洗与质检 -> TA-4 数据切分`

## 2. TA-1：标签与评估口径冻结

### 2.1 标签体系

本研究采用三分类情感体系：

- `negative = 0`
- `neutral = 1`
- `positive = 2`

对 Amazon 评分字段采用弱监督映射：

- 1~2 星 -> 0
- 3 星 -> 1
- 4~5 星 -> 2

### 2.2 六维与可解释约定

六维定义冻结为：优点、缺点、退货原因、购买动机、用户期望、应用场景。  
证据句结构约定包含 `evidence_quote` 与 `highlight_spans`（字符级起止索引），保证后续归因链路可追溯。

### 2.3 评估口径

RoBERTa 评估指标冻结为 `Accuracy + Macro-F1 + Confusion Matrix`，上线门槛 `Accuracy >= 85%`。

## 3. TA-2：训练数据契约冻结

### 3.1 统一字段

训练输入最小字段固定为：

`id, platform, product_id, raw_text, analysis_input_en, lang, created_at, source, label_sentiment`

### 3.2 数据路径与切分规则

- 原始：`finetune/data/raw/reviews.csv`
- 清洗后：`finetune/data/processed/reviews_cleaned.csv`
- 切分：`finetune/data/splits/{train,val,test}.csv`
- 切分比例：`0.8 / 0.1 / 0.1`，随机种子 `42`，按 `label_sentiment` 分层。

## 4. TA-3：数据清洗与质检流程

### 4.1 原始数据导入

以 `Electronics_5.json`（Amazon Review Data 2018, 5-core）为输入，流式转换为契约 CSV：

- 输入：`finetune/data/raw/Electronics_5.json`
- 输出：`finetune/data/raw/reviews.csv`

### 4.2 清洗规则

清洗脚本执行以下规则：

1. 删除 `analysis_input_en` 为空的样本  
2. 文本长度过滤：保留 `5~1024` 字符  
3. 按 `id` 去重（保留首次出现）  
4. 大文件采用分块处理，避免内存溢出

### 4.3 本次运行结果

- 原始行数：`6,738,227`
- 清洗后：`5,960,107`
- 移除：`778,120`（`11.55%`）

清洗后标签分布：

- `label 0`: `670,083`
- `label 1`: `425,052`
- `label 2`: `4,864,972`

对应报告文件：`finetune/reports/ta3-cleaning-report.md`

## 5. TA-4：训练集构造与切分

### 5.1 切分执行

在清洗数据基础上执行分层切分，生成训练/验证/测试集。

### 5.2 本次切分结果

- train：`4,768,085`（80.00%）
- val：`596,011`（10.00%）
- test：`596,011`（10.00%）
- total：`5,960,107`

三份子集标签占比保持一致（分层成功）：

- label 0：`11.24%`
- label 1：`7.13%`
- label 2：`81.63%`

对应报告文件：`finetune/reports/ta4-split-report.md`

## 6. 与后续 TA-5 的衔接

完成 TA-4 后，已具备 RoBERTa 微调直接输入。  
下一步可在 Colab 执行 TA-5（`ml/data/splits/` 下放 `train.csv` / `val.csv` / `test.csv`，使用 `ml/configs/train_roberta_colab.yaml`；步骤见 `ml/docs/colab-minimal-start.md`）。

