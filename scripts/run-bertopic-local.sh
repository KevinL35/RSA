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
  echo "import-queue 离线脚本已下线：ml/scripts/import_bertopic_candidates_to_review_queue.py 不再维护。" >&2
  echo "请改用 apps/bertopic-api 的 HTTP 入队流程。" >&2
  exit 1
fi

case "$MODE" in
  help | -h | --help)
    cat <<'EOF'
BERTopic：日常用 HTTP 从 Supabase 挖掘（见 apps/bertopic-api/README.md）。POST /discover-from-supabase 默认已自动入词典审核队列（review_queue_import）。

本脚本仅在关闭自动入队（auto_import_review_queue: false）或需补录 JSONL 时使用：

  bash scripts/bertopic.sh
  # POST /discover-from-supabase；如需手写 JSONL，请自行保存到任意临时目录

导入队列（需 SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY，可读 apps/platform-api/.env）：

  # import-queue 已下线，请改用 bertopic-api 的自动入队

也可用样例测导入：ml/fixtures/bertopic_candidates_sample.jsonl

维护/单测离线 CLI 已下线，请统一走 apps/bertopic-api HTTP。
EOF
    ;;
  *)
    echo "未知子命令: $MODE。日常请用 apps/bertopic-api POST /discover-from-supabase（见 apps/bertopic-api/README.md）。" >&2
    echo "仅支持: import-queue、help" >&2
    exit 1
    ;;
esac
