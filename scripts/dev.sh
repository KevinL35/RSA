#!/usr/bin/env bash
# 本地一键启动：analysis-api (8089) + platform-api (8000) + deepseek-adapter (9100, 可选) + Web (Vite)
# 用法：在仓库根目录执行  bash scripts/dev.sh
# 可选：ANALYSIS_PORT=8089 API_PORT=8000 ADAPTER_PORT=9100 bash scripts/dev.sh
# 跳过适配层：SKIP_DEEPSEEK_ADAPTER=1 bash scripts/dev.sh

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

# 自动执行 Supabase 迁移（默认开启；无 SUPABASE_DB_URL 或无 psql 会自动跳过）
if [[ "${SUPABASE_AUTO_MIGRATE:-1}" == "1" ]]; then
  bash "${ROOT}/scripts/apply-supabase-migrations.sh" || true
fi

ANALYSIS_PID=""
API_PID=""
ADAPTER_PID=""

cleanup() {
  if [[ -n "${API_PID}" ]]; then kill "${API_PID}" 2>/dev/null || true; fi
  if [[ -n "${ANALYSIS_PID}" ]]; then kill "${ANALYSIS_PID}" 2>/dev/null || true; fi
  if [[ -n "${ADAPTER_PID}" ]]; then kill "${ADAPTER_PID}" 2>/dev/null || true; fi
}
trap cleanup EXIT INT TERM

ANALYSIS_PORT="${ANALYSIS_PORT:-8089}"
API_PORT="${API_PORT:-8000}"
ADAPTER_PORT="${ADAPTER_PORT:-9100}"

pick_shared_python() {
  if [[ -x "${ROOT}/.venv/bin/python" ]]; then
    echo "${ROOT}/.venv/bin/python"
  else
    echo "python3"
  fi
}

ensure_uvicorn() {
  local app_dir="$1"
  local py_bin="$2"
  if ! "${py_bin}" -c "import uvicorn" >/dev/null 2>&1; then
    echo "[dev] ${app_dir} 使用的 Python 无法 import uvicorn：${py_bin}"
    echo "  可执行：cd ${app_dir} && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
    exit 1
  fi
}

ANALYSIS_PY="$(pick_shared_python)"
API_PY="$(pick_shared_python)"
ensure_uvicorn "apps/analysis-api" "${ANALYSIS_PY}"
ensure_uvicorn "apps/platform-api" "${API_PY}"

# 主题挖掘子进程解释器（Platform API 子进程跑 bertopic_supabase_pools.py）：
# 优先级：已有 TOPIC_MINING_PYTHON → 仓库根 .venv-topic →
#（可选）自动创建 ROOT/.venv-topic 并 pip install
# 跳过自动安装：SKIP_TOPIC_VENV_BOOTSTRAP=1 bash scripts/dev.sh
_topic_python_imports_bertopic() {
  local py="$1"
  [[ -x "${py}" ]] && "${py}" -c "import bertopic" >/dev/null 2>&1
}

if [[ -z "${TOPIC_MINING_PYTHON:-}" ]]; then
  for cand in "${ROOT}/.venv-topic/bin/python"; do
    if [[ -x "${cand}" ]] && _topic_python_imports_bertopic "${cand}"; then
      export TOPIC_MINING_PYTHON="${cand}"
      echo "[dev] TOPIC_MINING_PYTHON=${TOPIC_MINING_PYTHON}"
      break
    fi
  done
fi

if [[ -z "${TOPIC_MINING_PYTHON:-}" ]] && [[ "${SKIP_TOPIC_VENV_BOOTSTRAP:-}" != "1" ]]; then
  VENV_TOPIC="${ROOT}/.venv-topic"
  PY_TOPIC="${VENV_TOPIC}/bin/python"
  if [[ ! -x "${PY_TOPIC}" ]]; then
    echo "[dev] 创建 ${VENV_TOPIC} 供主题挖掘使用…"
    python3 -m venv "${VENV_TOPIC}"
  fi
  if [[ -x "${PY_TOPIC}" ]] && ! _topic_python_imports_bertopic "${PY_TOPIC}"; then
    echo "[dev] 在 .venv-topic 中安装主题挖掘依赖（ml/requirements-topic-pools.txt，首次可能较久、需联网）…"
    if ! "${PY_TOPIC}" -m pip install -r "${ROOT}/ml/requirements-topic-pools.txt"; then
      echo "[dev] 警告：主题依赖安装失败，主题挖掘任务可能不可用；可手动执行："
      echo "  ${PY_TOPIC} -m pip install -r ${ROOT}/ml/requirements-topic-pools.txt"
    fi
  fi
  if _topic_python_imports_bertopic "${PY_TOPIC}"; then
    export TOPIC_MINING_PYTHON="${PY_TOPIC}"
    echo "[dev] TOPIC_MINING_PYTHON=${TOPIC_MINING_PYTHON}"
  fi
fi

if [[ -z "${TOPIC_MINING_PYTHON:-}" ]]; then
  echo "[dev] 未配置含 BERTopic 的解释器；主题挖掘子进程将用 Platform API 默认 Python（通常无法 import bertopic）。"
  echo "[dev] 可去掉 SKIP_TOPIC_VENV_BOOTSTRAP 后重试，或手动：python3 -m venv ${ROOT}/.venv-topic && ${ROOT}/.venv-topic/bin/pip install -r ${ROOT}/ml/requirements-topic-pools.txt"
fi

(
  cd apps/analysis-api
  # 与 platform-api 一样启用 --reload：改词典/分析逻辑后无需手杀进程（否则易仍跑旧代码，例如已移除的 seed 非空校验）
  exec "${ANALYSIS_PY}" -m uvicorn app.main:app --reload --host 127.0.0.1 --port "${ANALYSIS_PORT}"
) &
ANALYSIS_PID=$!

(
  cd apps/platform-api
  exec "${API_PY}" -m uvicorn app.main:app --reload --host 0.0.0.0 --port "${API_PORT}"
) &
API_PID=$!

# DeepSeek 适配层（TB-3 /analyze + AI 摘要 /insight-summary + Agent /agent-enrich）
# 跳过：SKIP_DEEPSEEK_ADAPTER=1 bash scripts/dev.sh
ADAPTER_DIR="${ROOT}/apps/deepseek-adapter"
if [[ "${SKIP_DEEPSEEK_ADAPTER:-}" == "1" ]]; then
  echo "[dev] SKIP_DEEPSEEK_ADAPTER=1，未启动 deepseek-adapter（AI 摘要 / DeepSeek 路由不可用）"
elif [[ ! -d "${ADAPTER_DIR}" ]]; then
  echo "[dev] 未发现 ${ADAPTER_DIR}，跳过 deepseek-adapter"
else
  ADAPTER_PY="$(pick_shared_python)"
  if ! "${ADAPTER_PY}" -c "import uvicorn,openai" >/dev/null 2>&1; then
    echo "[dev] deepseek-adapter 依赖缺失，自动安装到 ${ADAPTER_DIR}/.venv …"
    if [[ ! -x "${ADAPTER_DIR}/.venv/bin/python" ]]; then
      python3 -m venv "${ADAPTER_DIR}/.venv"
    fi
    ADAPTER_PY="${ADAPTER_DIR}/.venv/bin/python"
    if ! "${ADAPTER_PY}" -m pip install -r "${ADAPTER_DIR}/requirements.txt"; then
      echo "[dev] 警告：deepseek-adapter 依赖安装失败，AI 摘要将不可用"
      ADAPTER_PY=""
    fi
  fi
  if [[ -n "${ADAPTER_PY}" ]]; then
    ADAPTER_KEY_PRESENT=0
    if [[ -n "${DEEPSEEK_API_KEY:-}" ]]; then
      ADAPTER_KEY_PRESENT=1
    elif [[ -f "${ADAPTER_DIR}/.env" ]] && grep -q '^DEEPSEEK_API_KEY=..' "${ADAPTER_DIR}/.env"; then
      ADAPTER_KEY_PRESENT=1
    fi
    if [[ "${ADAPTER_KEY_PRESENT}" != "1" ]]; then
      echo "[dev] 警告：未检测到 DEEPSEEK_API_KEY（环境变量或 ${ADAPTER_DIR}/.env），AI 摘要将返回 503"
    fi
    (
      cd "${ADAPTER_DIR}"
      exec "${ADAPTER_PY}" -m uvicorn main:app --reload --host 127.0.0.1 --port "${ADAPTER_PORT}"
    ) &
    ADAPTER_PID=$!
  fi
fi

echo "[dev] Analysis API     http://127.0.0.1:${ANALYSIS_PORT}/health"
echo "[dev] Platform API     http://127.0.0.1:${API_PORT}/docs"
if [[ -n "${ADAPTER_PID}" ]]; then
  echo "[dev] DeepSeek adapter http://127.0.0.1:${ADAPTER_PORT}/health"
fi
echo "[dev] Web              见下方 Vite 地址（Ctrl+C 将结束全部服务）"
sleep 1

cd apps/web
if [[ ! -d node_modules ]]; then
  echo "[dev] 首次运行：npm install …"
  npm install
fi
npm run dev
