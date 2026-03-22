# Analysis API（自研模型推理服务 / TA-11）

目录名 **`apps/analysis-api`**：在 **不依赖外部大模型 API** 的情况下，为 `apps/platform-api` 的 `POST .../insight-tasks/{id}/analyze` 提供 HTTP 分析源：**情感**（可选 RoBERTa 微调权重）+ **六维词典归因**（`ml/scripts/attribution_engine.py`）。**未设置** `TAXONOMY_YAML` 时：词典 **仅** 从 **`public.taxonomy_entries`**（Supabase）读取 seed + 各垂直 overlay，与 API `taxonomy-preview` 一致；须配置 **`SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`**，且库内 seed **非空**（可用 `scripts/seed_taxonomy_yaml_to_supabase.py` 从 **`ml/fixtures/taxonomy/`** 导入）。显式设置 `TAXONOMY_YAML` 时仅加载该单文件（调试用，不走库）。

## 请求与响应

与 `apps/platform-api` 发出的一致：JSON 含 `insight_task_id`、`platform`、`product_id`、`analysis_provider_id`、可选 `dictionary_vertical_id`、`reviews[]`（`id`、`raw_text`、`rating` 等）。响应顶层为 `reviews` 数组，元素含 `review_id`、`sentiment`、`dimensions`（与 `packages/contracts/src/analysis.ts` 对齐）。

## 一键启动（Analysis API + Platform API + 前端）

在仓库根目录（需已建好 `apps/analysis-api/.venv` 与 `apps/platform-api/.venv` 并 `npm install` 过 `apps/web`）：

```bash
bash scripts/dev-all.sh
```

按 `Ctrl+C` 会结束三个服务。单独启动仍见下文。

## 安装与启动

在仓库根目录外亦可，建议：

```bash
cd apps/analysis-api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# 可选：启用 TA-5 权重（需 GPU/CPU 与较长时间加载）
# pip install "transformers>=4.46,<6" "torch>=2.1.0"
```

启动：

```bash
cd apps/analysis-api
source .venv/bin/activate
# 可选：强制单文件词典；不设则按 dictionary_vertical_id 合并 seed+overlay（TA-10）
# export TAXONOMY_YAML="../../ml/fixtures/taxonomy/taxonomy_dictionary_seed_v1.yaml"
# 自研情感权重（仅本地，勿上传 Supabase）：目录须含 HuggingFace 结构（config.json、模型权重等）。
# 可将训练产物放在 ml/artifacts/rsa-v1/checkpoint-XXXXX，或把某 checkpoint 内容直接放在 rsa-v1 下。
# export SENTIMENT_MODEL_DIR="../../ml/artifacts/rsa-v1/checkpoint-59601"
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
