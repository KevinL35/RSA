#!/usr/bin/env bash
# 本地一键启动：rsa-model-api (8089) + API (8000) + Web (Vite)
# 用法：在仓库根目录执行  bash scripts/dev-all.sh
# 可选：ANALYSIS_PORT=8089 API_PORT=8000 bash scripts/dev-all.sh

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ANALYSIS_PID=""
API_PID=""

cleanup() {
  if [[ -n "${API_PID}" ]]; then kill "${API_PID}" 2>/dev/null || true; fi
  if [[ -n "${ANALYSIS_PID}" ]]; then kill "${ANALYSIS_PID}" 2>/dev/null || true; fi
}
trap cleanup EXIT INT TERM

ANALYSIS_PORT="${ANALYSIS_PORT:-8089}"
API_PORT="${API_PORT:-8000}"

if [[ ! -d apps/rsa-model-api/.venv ]]; then
  echo "[dev-all] 缺少 apps/rsa-model-api/.venv，请先执行："
  echo "  cd apps/rsa-model-api && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

if [[ ! -d apps/api/.venv ]]; then
  echo "[dev-all] 缺少 apps/api/.venv，请先执行："
  echo "  cd apps/api && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

(
  cd apps/rsa-model-api
  # shellcheck disable=SC1091
  source .venv/bin/activate
  exec uvicorn app.main:app --host 127.0.0.1 --port "${ANALYSIS_PORT}"
) &
ANALYSIS_PID=$!

(
  cd apps/api
  # shellcheck disable=SC1091
  source .venv/bin/activate
  exec uvicorn app.main:app --reload --host 0.0.0.0 --port "${API_PORT}"
) &
API_PID=$!

echo "[dev-all] Model API http://127.0.0.1:${ANALYSIS_PORT}/health"
echo "[dev-all] API       http://127.0.0.1:${API_PORT}/docs"
echo "[dev-all] Web       见下方 Vite 地址（Ctrl+C 将结束全部服务）"
sleep 1

cd apps/web
if [[ ! -d node_modules ]]; then
  echo "[dev-all] 首次运行：npm install …"
  npm install
fi
npm run dev
