# ml

模型与离线流程（原 `finetune` 已并入本目录）。在**仓库根目录**执行脚本时，路径以 `ml/...` 为准。

## 依赖

- `requirements-finetune.txt`：RoBERTa 微调与评估所需 Python 包。

## 目录与文件说明

| 路径 | 作用 |
|------|------|
| **`configs/data_contract.yaml`** | TA-3/TA-4 数据契约：必填列、`label_sentiment` 映射、清洗规则与路径占位。 |
| **`configs/train_roberta.yaml`** | 本地默认训练配置（相对路径 `finetune/...` 或 `ml/...` 以你本地为准），`split_dataset` / 训练共用。 |
| **`configs/train_roberta_colab.yaml`** | **Colab 默认**：`train.csv` / `val.csv` / `test.csv` 在 `ml/data/splits/`。 |
| **`configs/train_roberta_colab_shards.yaml`** | 可选：仅当 `train` 拆成多文件时需 glob 合并（见 `colab-minimal-start.md` 附录）。 |
| **`docs/colab-minimal-start.md`** | Colab 步骤说明（与下面笔记本二选一）。 |
| **`notebooks/ta5_roberta_colab.ipynb`** | 可上传 Colab 按格运行（含挂载 Drive、克隆、拷数据、训练、备份）。 |
| **`scripts/clean_data.py`** | 按 `data_contract.yaml` 清洗原始 CSV → `reviews_cleaned.csv`。 |
| **`scripts/split_dataset.py`** | 将清洗后数据按配置切分为 train/val/test。 |
| **`scripts/import_amazon2018_reviews_jsonl.py`** | 将 Amazon 2018 JSONL 转为契约 CSV（可选数据源）。 |
| **`scripts/import_amazon_fine_food_raw.py`** | 将 Amazon Fine Food CSV 转为契约格式（可选数据源）。 |
| **`scripts/csv_splits.py`** | 读入 split CSV：严格解析失败时宽松跳过坏行（引号/截断问题）。 |
| **`scripts/merge_train_shards.py`** | 可选：多个 train 分片合并为一个 `train.csv`。 |
| **`scripts/subset_splits.py`** | 从 `splits/` 对 train/val/test **各做分层 10%（可改比例）** → `splits_10pct/`，配合 `train_roberta_colab_10pct.yaml`。 |
| **`configs/train_roberta_colab_10pct.yaml`** | 一成数据训练：CSV 指向 `ml/data/splits_10pct/`，artifact 目录与全量区分。 |
| **`scripts/train_sentiment.py`** | RoBERTa 微调；兼容 transformers 4/5（`eval_strategy`、`Trainer.processing_class`）；可选 `--tokenized-cache-dir` 跳过重复 map。 |
| **`scripts/evaluate_sentiment.py`** | 加载已训练 checkpoint，在 `test.csv` 上评估并写报告。 |
| **`data/`** | 放置 `raw` / `processed` / `splits`（大文件勿提交 Git，见仓库 `.gitignore`）。 |
| **`artifacts/`** | 训练产出的模型与 checkpoint（勿提交 Git）。 |
| **`reports/`** | 清洗报告、评估 JSON 等输出（勿提交 Git）。 |

## 本地流水线（概要）

1. 准备 `data/raw` → `clean_data.py` → `split_dataset.py`（配置用 `train_roberta.yaml`）  
2. `train_sentiment.py` → `evaluate_sentiment.py`

Colab 仅用 Drive 数据时，见 **`docs/colab-minimal-start.md`**。
