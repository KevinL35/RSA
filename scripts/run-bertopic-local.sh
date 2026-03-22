#!/usr/bin/env bash
# 将 BERTopic 候选 JSONL 写入 Supabase dictionary_review_queue（仅需系统 python3）。
# 日常主题挖掘请用 apps/bertopic-api：bash scripts/bertopic.sh → POST /discover-from-supabase。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MODE="${1:-help}"
if [[ $# -ge 1 ]]; then
  shift
fi

if [[ "$MODE" == "import-queue" ]]; then
  if [[ $# -lt 1 ]]; then
    echo "用法: bash scripts/run-bertopic-local.sh import-queue <bertopic_candidates_*.jsonl> [--dry-run] [--skip-existing] [--vertical-id general]" >&2
    exit 1
  fi
  JSONL="$1"
  shift
  exec python3 "${ROOT}/ml/scripts/import_bertopic_candidates_to_review_queue.py" --jsonl "$JSONL" "$@"
fi

case "$MODE" in
  help | -h | --help)
    cat <<'EOF'
BERTopic：日常用 HTTP 从 Supabase 挖掘（见 apps/bertopic-api/README.md）。POST /discover-from-supabase 默认已自动入词典审核队列（review_queue_import）。

本脚本仅在关闭自动入队（auto_import_review_queue: false）或需补录 JSONL 时使用：

  bash scripts/bertopic.sh
  # POST /discover-from-supabase；若需手写 JSONL：jq -c '.candidates[]' resp.json > ml/reports/bertopic_candidates.jsonl

导入队列（需 SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY，可读 apps/platform-api/.env）：

  bash scripts/run-bertopic-local.sh import-queue ml/reports/bertopic_candidates_xxx.jsonl --skip-existing

也可用样例测导入：ml/fixtures/bertopic_candidates_sample.jsonl

维护/单测如需直接跑 CLI：python ml/scripts/run_bertopic_offline.py --help（非日常路径）。
EOF
    ;;
  *)
    echo "未知子命令: $MODE。日常请用 apps/bertopic-api POST /discover-from-supabase（见 apps/bertopic-api/README.md）。" >&2
    echo "仅支持: import-queue、help" >&2
    exit 1
    ;;
esac
