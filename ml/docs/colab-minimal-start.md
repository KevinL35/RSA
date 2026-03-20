# Colab 版最小启动命令清单（TA-5）

本清单用于在 Colab 上最小成本启动 RoBERTa 微调。

## 0) 前提

- 你本地已完成 TA-4，并有以下文件：
  - `finetune/data/splits/train.csv`
  - `finetune/data/splits/val.csv`
  - `finetune/data/splits/test.csv`
- `finetune/configs/train_roberta_colab.yaml`
  - `finetune/scripts/train_sentiment.py`
  - `finetune/scripts/evaluate_sentiment.py`
- 将 `finetune/` 上传到 Google Drive（建议目录：`MyDrive/RSA/finetune`）。

## 1) 挂载 Drive

```python
from google.colab import drive
drive.mount('/content/drive')
```

## 2) 进入项目目录并安装依赖

```bash
%cd /content/drive/MyDrive/RSA
pip install -r finetune/requirements.txt
```

## 3) 训练（TA-5）

```bash
python finetune/scripts/train_sentiment.py --config finetune/configs/train_roberta_colab.yaml
```

默认产物目录：

- `finetune/artifacts/roberta-sentiment-v0-colab`

## 4) 测试集评估

```bash
python finetune/scripts/evaluate_sentiment.py \
  --config finetune/configs/train_roberta_colab.yaml \
  --checkpoint_dir finetune/artifacts/roberta-sentiment-v0-colab
```

默认报告路径：

- `finetune/reports/sentiment_eval_v0_colab.json`

## 5) 可选：先跑小样本烟雾测试（强烈建议）

本仓库已提供 `finetune/configs/train_roberta_colab.yaml` 作为 Colab 友好配置（`epoch=1`, `bs=8/16`）。

## 6) 常见问题

- `CUDA out of memory`：
  - 将 `per_device_train_batch_size` 从 `16` 降到 `8` 或 `4`
  - 将 `per_device_eval_batch_size` 从 `32` 降到 `16`
- 训练太慢：
  - 减少 epoch
  - 先跑小样本验证，再跑全量

