# RSA 本地分析服务（评论洞察 / TA-11）

在 **不依赖外部大模型 API** 的情况下，为 `apps/api` 的 `POST .../insight-tasks/{id}/analyze` 提供 HTTP 分析源：**情感**（可选 RoBERTa 微调权重）+ **六维词典归因**（`ml/scripts/attribution_engine.py` + `ml/configs/taxonomy_dictionary_seed_v1.yaml`）。

## 请求与响应

与 `apps/api` 发出的一致：JSON 含 `insight_task_id`、`platform`、`product_id`、`analysis_provider_id`、`reviews[]`（`id`、`raw_text`、`rating` 等）。响应顶层为 `reviews` 数组，元素含 `review_id`、`sentiment`、`dimensions`（与 `packages/contracts/src/analysis.ts` 对齐）。

## 一键启动（分析 + API + 前端）

在仓库根目录（需已建好 `apps/analysis-service/.venv` 与 `apps/api/.venv` 并 `npm install` 过 `apps/web`）：

```bash
bash scripts/dev-all.sh
```

按 `Ctrl+C` 会结束三个服务。单独启动仍见下文。

## 安装与启动

在仓库根目录外亦可，建议：

```bash
cd apps/analysis-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# 可选：启用 TA-5 权重（需 GPU/CPU 与较长时间加载）
# pip install "transformers>=4.46,<6" "torch>=2.1.0"
```

启动：

```bash
cd apps/analysis-service
source .venv/bin/activate
export TAXONOMY_YAML="../../ml/configs/taxonomy_dictionary_seed_v1.yaml"   # 可选，默认即用仓库内该文件
# export SENTIMENT_MODEL_DIR="../../ml/artifacts/roberta-sentiment-v0-colab-10pct/checkpoint-59601"
uvicorn app.main:app --host 127.0.0.1 --port 8089
```

## 与 API 联调

`apps/api/.env` 示例（任务上 `analysis_provider_id` 为 `ins_builtin` 时 **必须** 为同名 key 配 URL）：

```env
ANALYSIS_PROVIDER_ROUTES_JSON={"ins_builtin":"http://127.0.0.1:8089/analyze","default":"http://127.0.0.1:8089/analyze"}
```

未配置 `SENTIMENT_MODEL_DIR` 时，情感使用 **星级**（若有）+ **轻量关键词启发式**；配置后优先 **RoBERTa**。

## 健康检查

`GET http://127.0.0.1:8089/health`
