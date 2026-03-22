# ml

模型与离线流程（原 `finetune` 已并入本目录）。在**仓库根目录**执行脚本时，路径以 `ml/...` 为准。

## 依赖

- `requirements-finetune.txt`：RoBERTa 微调与评估所需 Python 包。
- `requirements-bertopic.txt`：TA-9 离线 BERTopic（在 finetune 依赖基础上增加 `bertopic` / `sentence-transformers` 等）。

### BERTopic 本地（按需运行）

**不要**与 `bash scripts/dev-all.sh` 一起常驻启动：依赖重、耗时长，仅在需要产出主题候选时执行。

在**仓库根目录**：

```bash
bash scripts/run-bertopic-local.sh help     # 查看说明
bash scripts/run-bertopic-local.sh dry-run  # 不加载模型，只写 manifest（校验切片）
bash scripts/run-bertopic-local.sh full     # 用 fixtures 小样本跑通全流程 → `ml/reports/`
```

- 使用独立虚拟环境：`ml/.venv-bertopic/`（已 `.gitignore`）。
- 小样本配置：`configs/bertopic_batch_strategy_local.yaml`、`configs/bertopic_run_local.yaml`；**正式语料**请改回 `bertopic_batch_strategy_v1.yaml` / `bertopic_run_v1.yaml`（每切片通常 ≥200 条）。
- 自定义语料：`bash scripts/run-bertopic-local.sh custom --corpus-csv path/to.csv …`（其余参数同 `run_bertopic_offline.py`）。
- **从 Supabase 拉评论**：洞察任务写入的 `public.reviews` 可先导出为 BERTopic CSV（`text_en` ← `raw_text`，`created_at` 转 Unix 秒），再跑离线脚本：
  - `python ml/scripts/export_reviews_corpus_for_bertopic.py --out ml/data/bertopic_corpus_from_supabase.csv`（需 `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`，可读 `apps/api/.env`）
  - 或一键：`bash scripts/run-bertopic-local.sh from-db-dry` / `from-db-full`（支持附加 `--platform` / `--product-id` / `--limit` 等导出参数）

**BERTopic → 词典审核（闭环）**

1. 跑离线主题：`run_bertopic_offline.py` 或 `bash scripts/run-bertopic-local.sh full` / `from-db-full` 等 → `ml/reports/bertopic_candidates_{batch_id}.jsonl`
2. 导入待办队列：`python ml/scripts/import_bertopic_candidates_to_review_queue.py --jsonl ml/reports/bertopic_candidates_xxx.jsonl`（或 `bash scripts/run-bertopic-local.sh import-queue …`；可加 `--dry-run` / `--skip-existing`）。**尚未跑过 BERTopic 时**可用仓库内样例：`ml/fixtures/bertopic_candidates_sample.jsonl` 测导入。
3. Web **词典审核**：编辑规范词/同义词，选择**类目 + 六维**，通过 → `POST /api/v1/dictionary/approve-entry` 写入 `taxonomy_entries` overlay

## 目录与文件说明

| 路径 | 作用 |
|------|------|
| **`configs/data_contract.yaml`** | TA-3/TA-4 数据契约：必填列、`label_sentiment` 映射、清洗规则与路径占位。 |
| **`configs/train_roberta.yaml`** | 本地默认训练配置（相对路径 `finetune/...` 或 `ml/...` 以你本地为准），`split_dataset` / 训练共用。 |
| **`configs/train_roberta_colab.yaml`** | **Colab 默认**：`train.csv` / `val.csv` / `test.csv` 在 `ml/data/splits/`。 |
| **`configs/train_roberta_colab_shards.yaml`** | 可选：仅当 `train` 拆成多文件时需 glob 合并（见 `colab-minimal-start.md` 附录）。 |
| **`docs/colab-minimal-start.md`** | Colab 步骤说明（与下面笔记本二选一）。 |
| **`notebooks/ta5_roberta_colab.ipynb`** | 可上传 Colab 按格运行（含挂载 Drive、克隆、拷数据、训练、备份）。 |
| **`notebooks/ta5_roberta_autodl.ipynb`** | **AutoDL JupyterLab**：学术加速、`splits_10pct` / 全量可切换、训练与可选评估（长时间训练仍建议 SSH + `tmux`）。 |
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
| **`configs/bertopic_batch_strategy_v1.yaml`** | TA-8：BERTopic 离线语料字段、时间窗口、最小样本量、切片与调度默认值。 |
| **`configs/bertopic_batch_strategy_local.yaml`** | 本地联调：降低 `min_documents_product_slice`，配合 `fixtures/bertopic_corpus_sample.csv`。 |
| **`configs/bertopic_run_v1.yaml`** | TA-9：嵌入模型、`min_topic_size`、代表词/证据条数等运行超参。 |
| **`configs/bertopic_run_local.yaml`** | 本地联调：降低 `min_topic_size`，便于极小语料跑出主题。 |
| **`scripts/bertopic_offline_lib.py`** | TA-9：语料规范化、时间窗、切片与质量分 helper（无 bertopic 依赖，可单测）。 |
| **`scripts/run_bertopic_offline.py`** | TA-9：按切片跑 BERTopic → `ml/reports/bertopic_run_{batch_id}.json` + `bertopic_candidates_{batch_id}.jsonl`。 |
| **`scripts/export_reviews_corpus_for_bertopic.py`** | 从 Supabase `reviews` 导出 BERTopic 用 CSV（列：`id,platform,product_id,text_en,created_at`）。 |
| **`scripts/import_bertopic_candidates_to_review_queue.py`** | 将 `bertopic_candidates_*.jsonl` 写入 `dictionary_review_queue`，供词典审核页处理。 |
| **`fixtures/bertopic_corpus_sample.csv`** | 极小样例（用于 `--dry-run` 验证流程；正式跑批需 ≥200 条/切片）。 |
| **`tests/test_bertopic_offline_lib.py`** | TA-9：切片与窗口等纯逻辑测试（`pytest ml/tests/`，需已安装 `pandas`/`pyyaml`）。 |
| **`fixtures/taxonomy/*.yaml`** | TA-6/TA-10：种子与各垂直 overlay 样例；**仅用于** `scripts/seed_taxonomy_yaml_to_supabase.py` 灌库；运行时以库为准。 |
| **`scripts/taxonomy_supabase_toolkit.py`** | TA-10：脚本侧 Supabase overlay 全量替换 / 导出快照。 |
| **`scripts/taxonomy_backfill_lib.py`** | TA-10：决策校验、YAML 快照读写、审计行。 |
| **`scripts/publish_taxonomy_backfill.py`** | TA-10：将审核 JSONL 合并进 **Supabase overlay**，写 YAML 快照 + `taxonomy_backfill_audit.jsonl`。 |
| **`scripts/rollback_taxonomy_overlay.py`** | TA-10：用快照 YAML **覆盖 Supabase overlay** 并记审计。 |
| **`fixtures/taxonomy_decisions_sample.jsonl`** | TA-10：决策文件样例（approve + reject）。 |
| **`tests/test_taxonomy_backfill_lib.py`** | TA-10：`pytest ml/tests/test_taxonomy_backfill_lib.py`（需 `pyyaml`）。 |
| **`fixtures/attribution_eval_sample.csv`** | TA-7：抽检样例（可选列 `expected_dimensions`）。 |
| **`scripts/attribution_engine.py`** | TA-7：对 `analysis_input_en` 做词典匹配，产出与 `packages/contracts` 对齐的 `dimensions`（含 `evidence_quote` / `highlight_spans`）。 |
| **`scripts/evaluate_attribution.py`** | TA-7：批量跑抽检 CSV → `ml/reports/attribution_eval_v1.json`（可追溯率、双次运行确定性摘要）。 |

规则说明见 **`docs/stage-a/ecommerce-review-insights-v1-ta6-dictionary-and-matching-rules.md`**。

在线 **`apps/api` → `analyze`** 调用该归因引擎时，请运行 **`apps/rsa-model-api`**（见该目录 `README.md`），无需把 `ml/scripts` 嵌进 FastAPI 进程。

**自研情感模型（RoBERTa）推理路径**：推荐 **`ml/artifacts/rsa-v1/`**（一成训练见 `configs/train_roberta_colab_10pct.yaml` 的 `output_dir`）；`apps/rsa-model-api` 通过环境变量 **`SENTIMENT_MODEL_DIR`** 指向具体 checkpoint 目录。权重仅存部署机，**不**放 Supabase。

## 本地流水线（概要）

1. 准备 `data/raw` → `clean_data.py` → `split_dataset.py`（配置用 `train_roberta.yaml`）  
2. `train_sentiment.py` → `evaluate_sentiment.py`

Colab 仅用 Drive 数据时，见 **`docs/colab-minimal-start.md`**。

BERTopic 离线发现（TA-9）：见 **`docs/stage-a/ecommerce-review-insights-v1-ta9-bertopic-offline-discovery.md`**；安装 `requirements-bertopic.txt` 后于仓库根目录执行 `python ml/scripts/run_bertopic_offline.py --help`。

词典回灌（TA-10）：见 **`docs/stage-a/ecommerce-review-insights-v1-ta10-taxonomy-backfill.md`**；`python ml/scripts/publish_taxonomy_backfill.py --help`。
