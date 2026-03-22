#!/usr/bin/env bash
# 一键启动 BERTopic HTTP 服务（apps/bertopic-api，默认 8090）
# 用法：在仓库根目录执行  bash scripts/run-bertopic-api.sh
# 可选：BERTOPIC_PORT=8090 bash scripts/run-bertopic-api.sh

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -f "${ROOT}/apps/platform-api/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${ROOT}/apps/platform-api/.env"
  set +a
fi

BERTOPIC_PORT="${BERTOPIC_PORT:-8090}"

if [[ ! -d "${ROOT}/apps/bertopic-api/.venv" ]]; then
  echo "[bertopic-api] 缺少 apps/bertopic-api/.venv，请先执行："
  echo "  cd apps/bertopic-api && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

cd "${ROOT}/apps/bertopic-api"
# shellcheck disable=SC1091
source .venv/bin/activate

echo "[bertopic-api] http://127.0.0.1:${BERTOPIC_PORT}/health  |  POST /discover-from-supabase"
exec uvicorn app.main:app --host 127.0.0.1 --port "${BERTOPIC_PORT}"
