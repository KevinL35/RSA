#!/usr/bin/env bash
# BERTopic 离线发现：按需本地运行（不随 dev-all 启动）。
# 用法（在仓库根目录）：
#   bash scripts/run-bertopic-local.sh dry-run    # 不加载模型，只写 manifest（最快）
#   bash scripts/run-bertopic-local.sh full       # 用小样例 CSV 跑完整 BERTopic（首次会下载嵌入模型）
#   bash scripts/run-bertopic-local.sh custom --corpus-csv path.csv [-- 其他 run_bertopic_offline.py 参数]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VENV="${ROOT}/ml/.venv-bertopic"
MODE="${1:-help}"
if [[ $# -ge 1 ]]; then
  shift
fi

# 仅标准库 + HTTP，无需 BERTopic 虚拟环境
if [[ "$MODE" == "import-queue" ]]; then
  if [[ $# -lt 1 ]]; then
    echo "用法: bash scripts/run-bertopic-local.sh import-queue <ml/reports/bertopic_candidates_*.jsonl> [--dry-run] [--skip-existing] [--vertical-id general]"
    exit 1
  fi
  JSONL="$1"
  shift
  exec python3 "${ROOT}/ml/scripts/import_bertopic_candidates_to_review_queue.py" --jsonl "$JSONL" "$@"
fi

if [[ ! -d "$VENV" ]]; then
  echo "[bertopic-local] 创建虚拟环境: $VENV"
  python3 -m venv "$VENV"
fi
# shellcheck disable=SC1091
source "${VENV}/bin/activate"

echo "[bertopic-local] 安装/更新依赖（bertopic + sentence-transformers 等，首次较慢）…"
pip install -r "${ROOT}/ml/requirements-bertopic.txt" -q

CORPUS_DEFAULT="${ROOT}/ml/fixtures/bertopic_corpus_sample.csv"
STRAT_LOCAL="${ROOT}/ml/configs/bertopic_batch_strategy_local.yaml"
RUN_LOCAL="${ROOT}/ml/configs/bertopic_run_local.yaml"
RUN_V1="${ROOT}/ml/configs/bertopic_run_v1.yaml"
STRAT_V1="${ROOT}/ml/configs/bertopic_batch_strategy_v1.yaml"
BATCH_ID_LOCAL="local-demo"

case "$MODE" in
  from-db-dry)
    python "${ROOT}/ml/scripts/export_reviews_corpus_for_bertopic.py" --out "${ROOT}/ml/data/bertopic_corpus_from_supabase.csv" "$@"
    exec python "${ROOT}/ml/scripts/run_bertopic_offline.py" \
      --corpus-csv "${ROOT}/ml/data/bertopic_corpus_from_supabase.csv" \
      --batch-strategy "$STRAT_LOCAL" \
      --batch-id "${BATCH_ID_LOCAL}-db" \
      --dry-run \
      --force
    ;;
  from-db-full)
    python "${ROOT}/ml/scripts/export_reviews_corpus_for_bertopic.py" --out "${ROOT}/ml/data/bertopic_corpus_from_supabase.csv" "$@"
    exec python "${ROOT}/ml/scripts/run_bertopic_offline.py" \
      --corpus-csv "${ROOT}/ml/data/bertopic_corpus_from_supabase.csv" \
      --batch-strategy "$STRAT_V1" \
      --run-config "$RUN_V1" \
      --batch-id "${BATCH_ID_LOCAL}-db" \
      --force
    ;;
  dry-run)
    exec python "${ROOT}/ml/scripts/run_bertopic_offline.py" \
      --corpus-csv "$CORPUS_DEFAULT" \
      --batch-strategy "$STRAT_LOCAL" \
      --batch-id "$BATCH_ID_LOCAL" \
      --dry-run \
      --force
    ;;
  full)
    exec python "${ROOT}/ml/scripts/run_bertopic_offline.py" \
      --corpus-csv "$CORPUS_DEFAULT" \
      --batch-strategy "$STRAT_LOCAL" \
      --run-config "$RUN_LOCAL" \
      --batch-id "$BATCH_ID_LOCAL" \
      --force
    ;;
  custom)
    exec python "${ROOT}/ml/scripts/run_bertopic_offline.py" "$@"
    ;;
  help | -h | --help)
    cat <<'EOF'
BERTopic 本地（按需运行，与前后端 dev-all 无关）

  bash scripts/run-bertopic-local.sh dry-run   # 校验切片与 manifest，不加载深度学习模型
  bash scripts/run-bertopic-local.sh full      # 用 fixtures 小 CSV 跑通全流程，产出见 ml/reports/

从 Supabase reviews 表导出再跑（需 apps/api/.env 或环境中已有 SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY）：

  bash scripts/run-bertopic-local.sh from-db-dry   # 先导出 ml/data/bertopic_corpus_from_supabase.csv，再 dry-run
  bash scripts/run-bertopic-local.sh from-db-full  # 导出后用正式 v1 切片/超参跑 BERTopic（每平台+商品通常 ≥200 条）
  bash scripts/run-bertopic-local.sh from-db-dry --platform amazon --product-id B0XXXXXXXXX

将 BERTopic 产出的 JSONL 写入 Supabase 词典审核队列（仅需系统 python3 + Supabase 环境变量）：

  bash scripts/run-bertopic-local.sh import-queue ml/reports/bertopic_candidates_xxx.jsonl --skip-existing

自定义语料与参数（子命令 custom 之后原样传给 run_bertopic_offline.py）：

  bash scripts/run-bertopic-local.sh custom --corpus-csv path/to.csv --batch-strategy ml/configs/bertopic_batch_strategy_v1.yaml

说明：ml/reports/ 已在 .gitignore；正式跑批请用 v1 的 batch/run 配置（每切片通常 ≥200 条评论）。
EOF
    ;;
  *)
    echo "未知子命令: $MODE；执行 bash scripts/run-bertopic-local.sh help"
    exit 1
    ;;
esac
