#!/usr/bin/env bash
# 本地一键启动：analysis-api (8089) + platform-api (8000) + Web (Vite)
# 用法：在仓库根目录执行  bash scripts/dev.sh
# 可选：ANALYSIS_PORT=8089 API_PORT=8000 bash scripts/dev.sh

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

# 若存在各 app 的 .venv 则激活；否则使用当前环境的 python3（如 conda activate rsa）。
if ! python3 -c "import uvicorn" 2>/dev/null; then
  echo "[dev] 当前 python3 无法 import uvicorn。"
  echo "  请先激活已安装本仓库依赖的环境，例如：conda activate rsa"
  echo "  或按 app 使用独立虚拟环境，例如："
  echo "  cd apps/analysis-api && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

(
  cd apps/analysis-api
  if [[ -d .venv ]]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
  fi
  exec python3 -m uvicorn app.main:app --host 127.0.0.1 --port "${ANALYSIS_PORT}"
) &
ANALYSIS_PID=$!

(
  cd apps/platform-api
  if [[ -d .venv ]]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
  fi
  exec python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port "${API_PORT}"
) &
API_PID=$!

echo "[dev] Analysis API  http://127.0.0.1:${ANALYSIS_PORT}/health"
echo "[dev] Platform API  http://127.0.0.1:${API_PORT}/docs"
echo "[dev] Web       见下方 Vite 地址（Ctrl+C 将结束全部服务）"
sleep 1

cd apps/web
if [[ ! -d node_modules ]]; then
  echo "[dev] 首次运行：npm install …"
  npm install
fi
npm run dev
