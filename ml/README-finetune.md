# Stage A 微调模型项目脚手架

本目录用于实现 `docs/plans/ecommerce-review-insights-v1-plan.md` 中的 Stage A（模型微调与评估）。

## 目录说明

- `configs/`：训练与数据配置
- `data/`：原始、清洗后、切分后的数据（本仓库仅保留占位和样例）
- `scripts/`：可执行脚本（清洗、切分、训练、评估）
- `src/`：Python 包代码（后续可扩展）
- `reports/`：评估报告输出目录
- `artifacts/`：模型产物输出目录（权重、tokenizer、导出文件）

## 快速开始

1. 创建 Python 3.10+ 虚拟环境并安装依赖
2. 准备数据到 `finetune/data/raw/reviews.csv`
   - **Amazon Review Data (2018) 5-core JSONL**（如 `Electronics_5.json`）：先转为契约 CSV，再清洗（流式，可吃 GB 级文件）：

     ```bash
     python3 finetune/scripts/import_amazon2018_reviews_jsonl.py --input finetune/data/raw/Electronics_5.json --output finetune/data/raw/reviews.csv
     ```

     `overall` → `label_sentiment`（1–2→0，3→1，4–5→2），正文默认用 `reviewText`；可选 `--prepend-summary`。再用下面 `clean_data.py`（大文件会自动分块清洗）。

   - **Amazon Fine Food Reviews（CSV）**：

     ```bash
     python3 finetune/scripts/import_amazon_fine_food_raw.py --input /path/to/Reviews.csv
     ```

     **Score → label_sentiment** 规则同上；可选 `--prepend-summary`。

3. 依次执行（建议在仓库根目录运行）：
   - `python3 finetune/scripts/clean_data.py --config finetune/configs/data_contract.yaml`
   - `python3 finetune/scripts/split_dataset.py --config finetune/configs/train_roberta.yaml`
   - `python3 finetune/scripts/train_sentiment.py --config finetune/configs/train_roberta.yaml`
   - `python3 finetune/scripts/evaluate_sentiment.py --config finetune/configs/train_roberta.yaml --checkpoint_dir finetune/artifacts/roberta-sentiment-v0`

## 当前状态

当前为第一步初始化文件，脚本已提供参数与流程骨架，后续可直接补充业务逻辑并开始跑通。
