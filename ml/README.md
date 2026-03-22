# ml

模型与离线流程（原 `finetune` 已并入本目录）。在**仓库根目录**执行脚本时，路径以 `ml/...` 为准。

## 依赖

- `requirements-finetune.txt`：RoBERTa 微调与评估所需 Python 包。
- `requirements-bertopic.txt`：TA-9 离线 BERTopic（在 finetune 依赖基础上增加 `bertopic` / `sentence-transformers` 等）。

### BERTopic（日常：HTTP + Supabase）

**不要**与 `bash scripts/dev.sh` 一起常驻启动 **bertopic-api**：依赖重、耗时长。

1. **挖掘**：仓库根目录 `bash scripts/bertopic.sh`，请求 **`POST /discover-from-supabase`**（见 `apps/bertopic-api/README.md`）。服务内从 Supabase 导出语料并调用 `run_bertopic_discovery`。
2. **入队**：`POST /discover-from-supabase` 默认会把 `candidates` 自动写入 `dictionary_review_queue`（响应含 `review_queue_import`）。若关闭自动入队（`auto_import_review_queue: false`），可手写 JSONL：`jq -c '.candidates[]' resp.json > ml/reports/bertopic_candidates.jsonl`，再执行 `bash scripts/run-bertopic-local.sh import-queue <该文件>`。联调导入可用 `ml/fixtures/bertopic_candidates_sample.jsonl`。
3. **词典审核**：Web 端编辑后 → `POST /api/v1/dictionary/approve-entry` 写入 `taxonomy_entries` overlay。

**维护/单测**（非日常）：`python ml/scripts/run_bertopic_offline.py --help`；导出子进程仍用 `ml/scripts/export_reviews_corpus_for_bertopic.py`。联调超参见 `configs/bertopic_*_local.yaml` 与 API 请求体 `use_local_configs`。

## 目录与文件说明

| 路径 | 作用 |
|------|------|
| **`configs/data_contract.yaml`** | TA-3/TA-4 数据契约：必填列、`label_sentiment` 映射、清洗规则与路径占位。 |
| **`configs/train_roberta.yaml`** | 历史默认：`finetune/data/...` 与 `finetune/artifacts/...` 路径（旧布局）。 |
| **`configs/train_roberta_splits.yaml`** | **`ml/data/splits/`** 下 `train.csv` / `val.csv` / `test.csv` 的全量训练配置。 |
| **`configs/train_roberta_shards.yaml`** | 可选：`train` 拆成多 CSV 时用 glob 合并（见脚本说明）。 |
| **`configs/train_roberta_10pct.yaml`** | 一成子集：`ml/data/splits_10pct/`，产物目录 **`ml/artifacts/rsa-v1/`**（与线上一致）。 |
| **`scripts/clean_data.py`** | 按 `data_contract.yaml` 清洗原始 CSV → `reviews_cleaned.csv`。 |
| **`scripts/split_dataset.py`** | 将清洗后数据按配置切分为 train/val/test。 |
| **`scripts/import_amazon2018_reviews_jsonl.py`** | 将 Amazon 2018 JSONL 转为契约 CSV（可选数据源）。 |
| **`scripts/import_amazon_fine_food_raw.py`** | 将 Amazon Fine Food CSV 转为契约格式（可选数据源）。 |
| **`scripts/csv_splits.py`** | 读入 split CSV：严格解析失败时宽松跳过坏行（引号/截断问题）。 |
| **`scripts/merge_train_shards.py`** | 可选：多个 train 分片合并为一个 `train.csv`。 |
| **`scripts/subset_splits.py`** | 从 `splits/` 对 train/val/test **各做分层 10%（可改比例）** → `splits_10pct/`，配合 `train_roberta_10pct.yaml`。 |
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
| **`scripts/run_bertopic_offline.py`** | TA-9：按切片跑 BERTopic（**由 bertopic-api 调用**；CLI 仅维护/单测）。 |
| **`scripts/export_reviews_corpus_for_bertopic.py`** | 从 Supabase `reviews` 导出 BERTopic 用 CSV；可选 **`--insight-task-id` + `--only-without-dimension-hits`** 仅导出 A 类（有 `review_analysis`、无 `review_dimension_analysis` 行）。 |
| **`scripts/import_bertopic_candidates_to_review_queue.py`** | 将 `bertopic_candidates_*.jsonl` 写入 `dictionary_review_queue`（与 bertopic-api 默认自动入队逻辑一致，供补录/离线用）。 |
| **`scripts/bertopic_review_queue_import_lib.py`** | 候选 → 队列 REST 载荷与入库（供 `import_…` CLI 与 `apps/bertopic-api` 共用）。 |
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
| **`scripts/attribution_engine.py`** | TA-7：对 `analysis_input_en` 做词典匹配，产出与 API/前端约定一致的 `dimensions`（含 `evidence_quote` / `highlight_spans`）。 |
| **`scripts/evaluate_attribution.py`** | TA-7：批量跑抽检 CSV → `ml/reports/attribution_eval_v1.json`（可追溯率、双次运行确定性摘要）。 |

规则说明见 **`docs/stage-a/ecommerce-review-insights-v1-ta6-dictionary-and-matching-rules.md`**。

在线 **`apps/platform-api` → `analyze`** 调用该归因引擎时，请运行 **`apps/analysis-api`**（见该目录 `README.md`），无需把 `ml/scripts` 嵌进 FastAPI 进程。

**自研情感模型（RoBERTa）推理路径**：推荐 **`ml/artifacts/rsa-v1/`**（一成训练见 `configs/train_roberta_10pct.yaml` 的 `output_dir`）；`apps/analysis-api` 通过环境变量 **`SENTIMENT_MODEL_DIR`** 指向具体 checkpoint 目录。权重仅存部署机，**不**放 Supabase。

## 本地流水线（概要）

1. 准备 `data/raw` → `clean_data.py` → `split_dataset.py`（`ml/data/...` 管线用 **`train_roberta_splits.yaml`**）  
2. `train_sentiment.py` → `evaluate_sentiment.py`

BERTopic（TA-9）：日常见 **`apps/bertopic-api/README.md`**；规格与 CLI 细节见 **`docs/stage-a/ecommerce-review-insights-v1-ta9-bertopic-offline-discovery.md`**。

词典回灌（TA-10）：见 **`docs/stage-a/ecommerce-review-insights-v1-ta10-taxonomy-backfill.md`**；`python ml/scripts/publish_taxonomy_backfill.py --help`。
