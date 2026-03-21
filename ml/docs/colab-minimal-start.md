# Colab 版最小启动命令清单（TA-5）

在 Colab 上挂载 Drive 后微调 RoBERTa（与仓库 `ml/` 目录一致；若你 Drive 上仍用旧目录名 `finetune`，把下面命令里的 `ml` 全部改成 `finetune` 即可）。

## 0) 数据准备

- **单文件训练集**：`ml/data/splits/train.csv`、`val.csv`、`test.csv`（与本地 TA-4 一致）。
- **训练集拆成 5 份上传**：
  - 5 个文件 **表头一致**，与契约列一致（含 `analysis_input_en`、`label_sentiment`，建议含 `id`）。
  - 若文件名为 **`train.csv.part5-000` … `train.csv.part5-004`**（在 `ml/data/splits/`），默认配置已匹配：`train_csv_shard_glob: "ml/data/splits/train.csv.part5-*"`（按字典序合并，零填充序号顺序正确）。
  - 其它命名可改用 `train_part01.csv` … 等，并相应修改 yaml 里的 glob。
  - `val.csv`、`test.csv` 各一份即可。
  - 使用配置：`ml/configs/train_roberta_colab_shards.yaml`（训练时自动 `concat`，并按 `id` 去重）。

若 shard 文件名无规律，可在该 yaml 里删掉 `train_csv_shard_glob`，改用列表 `train_csv_shards`（见该文件同目录下 `train_roberta_colab.yaml` 所用字段名，训练脚本已支持）。

## 1) 挂载 Drive

```python
from google.colab import drive
drive.mount('/content/drive')
```

## 2) 进入仓库根目录并安装依赖

假设仓库在 `MyDrive/RSA`：

```bash
%cd /content/drive/MyDrive/RSA
pip install -q -r ml/requirements-finetune.txt
```

## 3) 训练（TA-5）

单文件 `train.csv`：

```bash
python ml/scripts/train_sentiment.py --config ml/configs/train_roberta_colab.yaml
```

训练集 5 分片：

```bash
python ml/scripts/train_sentiment.py --config ml/configs/train_roberta_colab_shards.yaml
```

产物目录默认：`ml/artifacts/roberta-sentiment-v0-colab`

## 4) 测试集评估

```bash
python ml/scripts/evaluate_sentiment.py \
  --config ml/configs/train_roberta_colab.yaml \
  --checkpoint_dir ml/artifacts/roberta-sentiment-v0-colab
```

（若用 shards 配置训练，把第一行 `--config` 改成 `train_roberta_colab_shards.yaml`，`checkpoint_dir` 相同即可。）

报告默认：`ml/reports/sentiment_eval_v0_colab.json`

## 5) 常见问题

- **CUDA out of memory**：在 yaml 里把 `per_device_train_batch_size` 改为 `4` 或 `2`；`per_device_eval_batch_size` 同步减小。
- **找不到分片**：确认当前工作目录是仓库根目录，且 glob 路径与 Drive 上实际路径一致；可在 Colab 里 `!ls ml/data/splits` 检查。
- **合并顺序错误**：重命名为带零填充的序号，或改用 `train_csv_shards` 显式列出 5 个路径。

## 6) 可选 Notebook

仓库内可复制：`ml/notebooks/ta5_roberta_colab.ipynb` 到 Colab 打开运行。
