# ml

训练与离线流程目录（已按子域拆分）：

- `ml/sentiment/`：情感模型数据处理、训练、评估
- `ml/topic_mining/`：主题挖掘与词典相关离线脚本（若安装）
- `ml/common/`：通用工具（如 CSV 读取 helper）

## 常用路径

- 情感脚本：`ml/sentiment/scripts/`
- 情感配置：`ml/sentiment/configs/`
- 情感数据：`ml/sentiment/data/`
- 情感报告：`ml/sentiment/reports/`
- 模型产物（独立目录）：`models/sentiment/`

## 情感训练流程（推荐）

在仓库根目录执行：

1. 清洗：
   - `python ml/sentiment/scripts/clean_data.py --config ml/sentiment/configs/data_contract.yaml`
2. 划分 train/val/test：
   - `python ml/sentiment/scripts/split_dataset.py --config ml/sentiment/configs/train_roberta_splits.yaml`
3. 训练：
   - `python ml/sentiment/scripts/train_sentiment.py --config ml/sentiment/configs/train_roberta_splits.yaml`
4. 评估：
   - `python ml/sentiment/scripts/evaluate_sentiment.py --config ml/sentiment/configs/train_roberta_splits.yaml --checkpoint_dir models/sentiment/roberta-sentiment-v0`

## 主题挖掘说明

BERTopic 以服务化优先（`apps/bertopic-api`）。若 `ml/topic_mining/scripts/` 下缺少离线脚本，
`bertopic-api` 会返回 503，提示离线脚本未安装/已下线。
