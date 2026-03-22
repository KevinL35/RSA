#!/usr/bin/env bash
# 本地一键启动：analysis-api (8089) + platform-api (8000) + Web (Vite)
# 用法：在仓库根目录执行  bash scripts/dev-all.sh
# 可选：ANALYSIS_PORT=8089 API_PORT=8000 bash scripts/dev-all.sh

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# apps/platform-api 通过 pydantic 读 apps/platform-api/.env；analysis-api 不会自动读该文件。
# 启动前注入同一 .env，避免分析阶段因缺 SUPABASE_* 读不到 taxonomy_entries 而 HTTP 500。
if [[ -f "${ROOT}/apps/platform-api/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${ROOT}/apps/platform-api/.env"
  set +a
fi

ANALYSIS_PID=""
API_PID=""

cleanup() {
  if [[ -n "${API_PID}" ]]; then kill "${API_PID}" 2>/dev/null || true; fi
  if [[ -n "${ANALYSIS_PID}" ]]; then kill "${ANALYSIS_PID}" 2>/dev/null || true; fi
}
trap cleanup EXIT INT TERM

ANALYSIS_PORT="${ANALYSIS_PORT:-8089}"
API_PORT="${API_PORT:-8000}"

if [[ ! -d apps/analysis-api/.venv ]]; then
  echo "[dev-all] 缺少 apps/analysis-api/.venv，请先执行："
  echo "  cd apps/analysis-api && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

if [[ ! -d apps/platform-api/.venv ]]; then
  echo "[dev-all] 缺少 apps/platform-api/.venv，请先执行："
  echo "  cd apps/platform-api && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

(
  cd apps/analysis-api
  # shellcheck disable=SC1091
  source .venv/bin/activate
  exec uvicorn app.main:app --host 127.0.0.1 --port "${ANALYSIS_PORT}"
) &
ANALYSIS_PID=$!

(
  cd apps/platform-api
  # shellcheck disable=SC1091
  source .venv/bin/activate
  exec uvicorn app.main:app --reload --host 0.0.0.0 --port "${API_PORT}"
) &
API_PID=$!

echo "[dev-all] Analysis API  http://127.0.0.1:${ANALYSIS_PORT}/health"
echo "[dev-all] Platform API  http://127.0.0.1:${API_PORT}/docs"
echo "[dev-all] Web       见下方 Vite 地址（Ctrl+C 将结束全部服务）"
sleep 1

cd apps/web
if [[ ! -d node_modules ]]; then
  echo "[dev-all] 首次运行：npm install …"
  npm install
fi
npm run dev
