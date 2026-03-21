# Colab 上 TA-5 微调：详细步骤

面向仓库 **`KevinL35/RSA`**，数据在 Google Drive：**`MyDrive/RSA/finetune/data/splits/`** 下的 `train.csv`、`val.csv`、`test.csv`。

---

## 一、开始前确认

1. **GitHub 仓库为公开**，否则 Colab 无法 `git clone`（私有库需配 token，本文不展开）。
2. **Drive 里三个文件** 已就位，且列包含：
   - **`analysis_input_en`**：英文输入文本  
   - **`label_sentiment`**：整数 **0 / 1 / 2**（负 / 中 / 正）
3. **本机已 push** 最新代码（含 `ml/scripts/train_sentiment.py`、`ml/configs/train_roberta_colab.yaml` 等）。

---

## 二、打开 Colab 并选 GPU

1. 打开 [Google Colab](https://colab.research.google.com/)。
2. 菜单 **「运行时」→「更改运行时类型」**。
3. **硬件加速器** 选 **T4 GPU**（或更高：L4、A100 等）；**不用 GPU** 会极慢甚至跑不动。
4. 保存。

---

## 三、方式 A：用仓库里的笔记本（推荐）

1. 在 GitHub 打开仓库 → 进入 **`ml/notebooks/ta5_roberta_colab.ipynb`** → 可在 Colab 用插件「在 Colab 中打开」，或下载 `.ipynb` 后在本页 **「文件」→「上传笔记本」**。
2. 若本地已有仓库：**先 `git pull`**，再上传最新的 `ta5_roberta_colab.ipynb`。
3. 从上到下**按顺序运行**每一个单元格（Shift+Enter）。

**第二格变量（一般不用改）：**

- `REPO_URL = "https://github.com/KevinL35/RSA.git"`
- `DRIVE_SPLITS = "/content/drive/MyDrive/RSA/finetune/data/splits"`

4. **挂载 Drive** 时，浏览器会弹出授权，点允许。
5. **第 4 格**会把 Drive 里三个 CSV **复制**到克隆下来的仓库 **`/content/RSA/ml/data/splits/`**（训练脚本只认这里的相对路径）。
6. **训练格**跑完后，看输出里是否有 **`Test metrics`**，无报错即成功。
7. **备份格**会把 `artifacts` 拷到 **`MyDrive/RSA/ml_artifacts_colab/`**，避免断开连接后 `/content` 被清空。

若你**不用 Drive 拷文件**（例如已手动上传到 Colab `RSA/ml/data/splits/`），可**跳过「第 4 格」复制**，直接跑「确认 `ls`」和训练。

---

## 四、方式 B：空白笔记本里手动输入（与笔记本等价）

### 1. 挂载 Drive

```python
from google.colab import drive
drive.mount("/content/drive")
```

### 2. 克隆代码（第一次）或更新（以后每次）

```bash
%cd /content
```

首次执行：

```bash
!git clone https://github.com/KevinL35/RSA.git
```

以后每次打开新会话可先：

```bash
%cd /content/RSA
!git pull
```

### 3. 安装依赖

```bash
%cd /content/RSA
!pip install -q -r ml/requirements-finetune.txt
```

### 4. 把 Drive 里的划分文件拷到仓库

```bash
%cd /content/RSA
!mkdir -p ml/data/splits
!cp "/content/drive/MyDrive/RSA/finetune/data/splits/train.csv" "ml/data/splits/"
!cp "/content/drive/MyDrive/RSA/finetune/data/splits/val.csv" "ml/data/splits/"
!cp "/content/drive/MyDrive/RSA/finetune/data/splits/test.csv" "ml/data/splits/"
!ls -la ml/data/splits/
```

应能看到三个文件及非零大小。

### 5. 训练

```bash
%cd /content/RSA
!python ml/scripts/train_sentiment.py --config ml/configs/train_roberta_colab.yaml
```

首次会从 Hugging Face 下载 **`roberta-base`**，需能访问外网。

### 6.（可选）单独再评测试集

```bash
%cd /content/RSA
!python ml/scripts/evaluate_sentiment.py \
  --config ml/configs/train_roberta_colab.yaml \
  --checkpoint_dir ml/artifacts/roberta-sentiment-v0-colab
```

### 7.（建议）备份到 Drive

```bash
!mkdir -p "/content/drive/MyDrive/RSA/ml_artifacts_colab"
!cp -r /content/RSA/ml/artifacts/roberta-sentiment-v0-colab "/content/drive/MyDrive/RSA/ml_artifacts_colab/"
!cp /content/RSA/ml/reports/sentiment_eval_v0_colab.json "/content/drive/MyDrive/RSA/ml_artifacts_colab/" 2>/dev/null || true
```

---

## 五、训练结果在哪里

| 内容 | 路径（在 `/content/RSA` 下） |
|------|------------------------------|
| 模型与 checkpoint | `ml/artifacts/roberta-sentiment-v0-colab/` |
| 测试集指标 JSON | `ml/reports/sentiment_eval_v0_colab.json` |

---

## 六、常见问题

| 现象 | 处理 |
|------|------|
| **最后一行出现 `^C` 但自己没按 Ctrl+C** | 在 Colab 里 **`^C` 一般表示进程收到了「中断」**，不一定是你键盘按的。常见原因：**① 点了工具栏「停止」**；**② 运行时崩溃**（尤其 **内存用尽**，加载/映射大 CSV 时 RAM 会飙高）；**③ 免费版会话被回收 / 断连**。请看 Colab **顶部是否出现黄色条**（如 *session crashed* / *out of memory*）。可先跑 `!free -h` 看内存；数据特别大时试 **「运行时 → 更改运行时类型 → 高 RAM」**，或暂时缩小 `train.csv` 做烟雾测试。 |
| **Roberta LOAD REPORT 里 MISSING / UNEXPECTED** | **正常现象**：分类头随机初始化、预训练里多出来的 `lm_head` 会丢弃。拉最新代码后脚本会压低这类日志；**不要因此中断训练**。 |
| **HF_TOKEN / unauthenticated** | 可选：在 Colab 执行 `from huggingface_hub import login; login()` 粘贴 token，减轻限速；不设也能训。 |
| **CUDA out of memory** | 编辑 `ml/configs/train_roberta_colab.yaml`，把 `per_device_train_batch_size` 改为 `4` 或 `2`。 |
| **找不到 CSV** | 检查 `cp` 源路径是否与 Drive 一致；在 Colab 左侧 **「文件」** 点开 `drive/MyDrive/RSA/finetune/data/splits` 核对文件名。 |
| **`git clone` 失败** | 确认仓库为 **HTTPS** 且 **公开**；不要用 `git@github.com` SSH 地址。 |
| **`ModuleNotFoundError`** | 确认 `%cd /content/RSA` 且在仓库根执行 `pip install -r ml/requirements-finetune.txt`。 |
| **CSV 解析报错** | 数据中有未闭合引号等；脚本会尽量跳过坏行，长期应在 TA-4 导出规范 CSV。 |
| **断开后模型没了** | Colab `/content` 不持久；务必执行备份到 **Drive**（方式 A 最后一格或方式 B 第 7 步）。 |

---

## 附录：训练集必须拆成多个文件时（可选）

1. 分片放在 `ml/data/splits/`，使用 **`ml/configs/train_roberta_colab_shards.yaml`**，或  
2. 用 **`ml/scripts/merge_train_shards.py`** 合并成单个 `train.csv` 后，仍用 **`train_roberta_colab.yaml`**。
