# Analysis API（自研模型推理服务 / TA-11）

目录名 **`apps/analysis-api`**：在 **不依赖外部大模型 API** 的情况下，为 `apps/platform-api` 的 `POST .../insight-tasks/{id}/analyze` 提供 HTTP 分析源：**情感**（可选 RoBERTa 微调权重）+ **六维词典归因**（`ml/topic_mining/scripts/attribution_engine.py`）；可选 **BERTopic 主题**（离线训练目录 + 句向量，见下文环境变量）。**未设置** `TAXONOMY_YAML` 时：词典 **仅** 从 **`public.taxonomy_entries`**（Supabase）读取 seed + 各垂直 overlay，与 API `taxonomy-preview` 一致；须配置 **`SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`**，且库内 seed **非空**。显式设置 `TAXONOMY_YAML` 时仅加载该单文件（调试用，不走库）。

## 请求与响应

与 `apps/platform-api` 发出的一致：JSON 含 `insight_task_id`、`platform`、`product_id`、`analysis_provider_id`、可选 `dictionary_vertical_id`、`reviews[]`（`id`、`raw_text`、`rating` 等）。响应顶层为 `reviews` 数组，元素含 `review_id`、`sentiment`、`dimensions`；若启用 BERTopic，另含 **`topic`**：`{ "id": int, "keywords": string[], "outlier": bool }`（与 Platform API 规范化后结构一致）。

## 一键启动（Analysis API + Platform API + 前端）

在仓库根目录（需已建好 `apps/analysis-api/.venv` 与 `apps/platform-api/.venv` 并 `npm install` 过 `apps/web`）：

```bash
bash scripts/dev.sh
```

按 `Ctrl+C` 会结束三个服务。单独启动仍见下文。

## 安装与启动

在仓库根目录外亦可，建议：

```bash
cd apps/analysis-api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# 可选：仅 RoBERTa 情感（无 BERTopic 时可不装 torch/transformers，见注释行）
# pip install "transformers>=4.46,<6" "torch>=2.1.0"
```

启用 **BERTopic 在线推理** 时需安装 `requirements.txt` 并**追加** `pip install -r ../../ml/requirements-bertopic.txt`（或等价依赖），并设置：

```bash
# 自仓库根目录起算的相对路径或绝对路径；指向 run_bertopic.py 保存的目录（如 bertopic_cli_1.0.0）
export BERTOPIC_MODEL_DIR="../../models/topic_mining/rsa-t1/bertopic_cli_1.0.0"
# 与训练 run_bertopic 时一致的 SentenceTransformer（目录或 Hub 名）
export TOPIC_EMBEDDING_MODEL_DIR="../../ml/all-MiniLM-L6-v2"
# 可选：encode 批大小
# export TOPIC_ENCODE_BATCH_SIZE=32
```

未设置上述两项时，行为与旧版一致（响应无 `topic` 字段）。

启动：

```bash
cd apps/analysis-api
source .venv/bin/activate
# 可选：强制单文件词典；不设则按 dictionary_vertical_id 合并 seed+overlay（TA-10）
# export TAXONOMY_YAML="../../ml/fixtures/taxonomy/taxonomy_dictionary_seed_v1.yaml"
# 自研情感权重（仅本地，勿上传 Supabase）：目录须含 HuggingFace 结构（config.json、模型权重等）。
# 可将训练产物放在 models/sentiment/rsa-v1/checkpoint-XXXXX，或把某 checkpoint 内容直接放在 rsa-v1 下。
# export SENTIMENT_MODEL_DIR="../../models/sentiment/rsa-v1/checkpoint-59601"
uvicorn app.main:app --host 127.0.0.1 --port 8089
```

## 与 API 联调

`apps/platform-api/.env` 示例（任务上 `analysis_provider_id` 为 `ins_builtin` 时 **必须** 为同名 key 配 URL）：

```env
ANALYSIS_PROVIDER_ROUTES_JSON={"ins_builtin":"http://127.0.0.1:8089/analyze","default":"http://127.0.0.1:8089/analyze"}
```

未配置 `SENTIMENT_MODEL_DIR` 时，情感使用 **星级**（若有）+ **轻量关键词启发式**；配置后优先 **RoBERTa**。

词典在 **Supabase** 或 **YAML** 中更新后，调用 `POST /admin/reload-taxonomy` 或重启进程以清空内存缓存。

## 健康检查

`GET http://127.0.0.1:8089/health`
