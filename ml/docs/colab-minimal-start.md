# Colab 上 TA-5 微调：完整流程（含每次拉代码）

面向仓库：**`https://github.com/KevinL35/RSA`**（公开、HTTPS）。  
数据在 Google Drive：**`MyDrive/RSA/finetune/data/splits/`** 下的 `train.csv`、`val.csv`、`test.csv`。

---

## 重要：每次在 Colab 开训前都要更新代码

- Colab **每次新会话**里 `/content` 往往是空的 → 需要 **`git clone`**。  
- 若目录里**已经有**旧的 `/content/RSA`（上次会话残留）→ **必须先 `git pull`**，否则会跑到过期的 `train_sentiment.py` / 配置。  
- **你在电脑改完代码并 `git push` 之后**，Colab 里**一定要再执行一次拉取**，再训练。

**推荐习惯：** 训练那一格之前，固定跑：

```bash
%cd /content/RSA
!git pull
```

若 `pull` 报错、目录乱了，可删掉重来（**会删掉未备份的 `/content/RSA` 里除 git 外的本地改动**）：

```bash
%cd /content
!rm -rf RSA
!git clone https://github.com/KevinL35/RSA.git
```

---

## 一、本机（开发机）先 push

在本地仓库执行，保证 GitHub 上是最新脚本与笔记本：

```bash
git add -A && git status
git commit -m "..."   # 有需要再提交
git push
```

---

## 二、Colab：选 GPU

1. 打开 [Google Colab](https://colab.research.google.com/)。  
2. **「运行时」→「更改运行时类型」** → **硬件加速器：T4 GPU**（或更高）→ 保存。

---

## 三、方式 A：用仓库笔记本（推荐）

1. 确保本机已 **push** 最新 `ml/notebooks/ta5_roberta_colab.ipynb`。  
2. Colab：**「文件」→「上传笔记本」**，选该 `.ipynb`（或从 GitHub 打开）。  
3. **从上到下依次运行**每个单元格。

**顺序说明：**

| 步骤 | 做什么 |
|------|--------|
| 第 2 格 | 配置 `REPO_URL`、`DRIVE_SPLITS`（默认已是 KevinL35 + `finetune/data/splits`，一般不改） |
| 挂载 Drive | 授权访问网盘 |
| **克隆 / `git pull`** | **没有** `RSA` 会 `clone`；**已有**会 **`pull`** → **这里就是在拉最新代码** |
| `pip install` | 安装 `ml/requirements-finetune.txt` |
| 拷贝 CSV | Drive → `ml/data/splits/` |
| `ls` | 确认三个文件 |
| 训练 | `train_sentiment.py` |
| （可选）评估 | `evaluate_sentiment.py` |
| （建议）备份 | `artifacts` → Drive `ml_artifacts_colab/` |

**若你昨天跑过、今天改了 GitHub：** 不要只靠旧会话里的代码；**新开运行时**或**至少再跑一遍「克隆 / pull」那一格**。

---

## 四、方式 B：空白笔记本 — 推荐命令顺序（可复制）

下面**每一块**单独成一个单元格，**按顺序执行**。

### 0）挂载 Drive

```python
from google.colab import drive
drive.mount("/content/drive")
```

### 1）拉代码：**clone（首次）或 pull（以后每次）**

```bash
%cd /content
```

**首次（没有 RSA 目录）：**

```bash
!git clone https://github.com/KevinL35/RSA.git
```

**以后每次（已有 RSA）：**

```bash
%cd /content/RSA
!git pull
```

**不确定有没有旧目录时，用这一条「万能」写法：**

```bash
%cd /content
import os
REPO = "/content/RSA"
if os.path.isdir(REPO + "/.git"):
    !git -C $REPO pull
else:
    !rm -rf $REPO && git clone https://github.com/KevinL35/RSA.git $REPO
!git -C $REPO log -1 --oneline
```

最后一行会打印**当前使用的最新 commit**，便于确认已更新。

### 2）安装依赖

```bash
%cd /content/RSA
!pip install -q -r ml/requirements-finetune.txt
```

### 3）拷贝划分数据到仓库

```bash
%cd /content/RSA
!mkdir -p ml/data/splits
!cp "/content/drive/MyDrive/RSA/finetune/data/splits/train.csv" "ml/data/splits/"
!cp "/content/drive/MyDrive/RSA/finetune/data/splits/val.csv" "ml/data/splits/"
!cp "/content/drive/MyDrive/RSA/finetune/data/splits/test.csv" "ml/data/splits/"
!ls -la ml/data/splits/
```

（若 CSV 不在上述路径，只改 `cp` 的源路径。）

### 4）训练

**首次**会完整 `map`（行数很大时可能要十几分钟）。**第二次起**建议把 **tokenized 缓存**放到 **Drive**（换 Colab 会话也不丢），可跳过漫长 map：

```bash
%cd /content/RSA
!python ml/scripts/train_sentiment.py --config ml/configs/train_roberta_colab.yaml \
  --tokenized-cache-dir "/content/drive/MyDrive/RSA/ml_tokenized_cache"
```

- 第一次跑完后会自动在 Drive 写入 `train/`、`val/`、`test/`。  
- **以后**只要该目录还在，会**直接加载**。  
- **换了 CSV** 后：在 Drive 里删掉 `ml_tokenized_cache`，或加 `--force-refresh-tokenized-cache`。

不配缓存（与旧行为相同，每次全量 map）：

```bash
%cd /content/RSA
!python ml/scripts/train_sentiment.py --config ml/configs/train_roberta_colab.yaml
```

### 5）（可选）测试集评估

```bash
%cd /content/RSA
!python ml/scripts/evaluate_sentiment.py \
  --config ml/configs/train_roberta_colab.yaml \
  --checkpoint_dir ml/artifacts/roberta-sentiment-v0-colab
```

### 6）（建议）备份到 Drive

```bash
!mkdir -p "/content/drive/MyDrive/RSA/ml_artifacts_colab"
!cp -r /content/RSA/ml/artifacts/roberta-sentiment-v0-colab "/content/drive/MyDrive/RSA/ml_artifacts_colab/"
!cp /content/RSA/ml/reports/sentiment_eval_v0_colab.json "/content/drive/MyDrive/RSA/ml_artifacts_colab/" 2>/dev/null || true
```

---

## 五、产物路径

| 内容 | 路径 |
|------|------|
| 模型 | `/content/RSA/ml/artifacts/roberta-sentiment-v0-colab/` |
| 报告 | `/content/RSA/ml/reports/sentiment_eval_v0_colab.json` |

---

## 六、数据列要求

- **`analysis_input_en`**、**`label_sentiment`**（0/1/2），与 `ml/configs/data_contract.yaml`、TA-1 一致。

---

## 七、常见问题

| 现象 | 处理 |
|------|------|
| **想确认 Colab 是否最新代码** | `!git -C /content/RSA log -1 --oneline`，与 GitHub 对比；不对则 `git pull` 或删目录后重新 `clone`。 |
| **最后一行 `^C` 但没按键盘** | Colab 里常表示进程被中断：误点「停止」、**内存不足**、会话断连等。模型下载完、出现 `Loading weights 100%` 之后，下一步会把 **CSV 全表 + tokenize** 载入内存，**数据很大时容易 RAM 爆**。看顶部黄条；`!wc -l ml/data/splits/train.csv` 看行数；**运行时选「高 RAM」**；或先**试跑子集**：`python ml/scripts/train_sentiment.py --config ... --max-train-rows 20000 --max-val-rows 2000 --max-test-rows 2000`（确认能跑通后再去掉参数全量训练）。 |
| **LOAD REPORT 里 MISSING / UNEXPECTED** | **正常**；分类头随机初始化。最新脚本已压低日志；不要因此点停止。 |
| **HF_TOKEN / unauthenticated** | 可选：`from huggingface_hub import login; login()`。 |
| **CUDA out of memory** | `train_roberta_colab.yaml` 里 `per_device_train_batch_size` 改为 `4` 或 `2`。 |
| **找不到 CSV** | 核对 Drive 路径与文件名。 |
| **`git clone` 失败** | 用 **HTTPS** 公开仓库，勿用 `git@github.com`。 |
| **`ModuleNotFoundError`** | 在 `/content/RSA` 下执行 `pip install -r ml/requirements-finetune.txt`。 |
| **CSV 解析报错** | 坏行会被跳过；长期应规范导出 CSV。 |
| **断开后模型没了** | 务必把 `artifacts` 备份到 Drive。 |

---

## 附录：训练集拆成多文件（可选）

1. 分片放 `ml/data/splits/`，用 **`train_roberta_colab_shards.yaml`**，或  
2. **`merge_train_shards.py`** 合并后再用 **`train_roberta_colab.yaml`**。
