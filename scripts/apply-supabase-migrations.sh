#!/usr/bin/env bash
# 自动执行 Supabase SQL 迁移（按 infra/migrations/ALL_FOR_SQL_EDITOR.sql）
#
# 需要：
# - SUPABASE_DB_URL（postgres 连接串，建议 service_role）
# 可选：
# - SUPABASE_AUTO_MIGRATE=1（由 dev.sh 控制是否调用）

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SQL_FILE="${ROOT}/infra/migrations/ALL_FOR_SQL_EDITOR.sql"

if [[ ! -f "${SQL_FILE}" ]]; then
  echo "[migrate] missing ${SQL_FILE}"
  exit 1
fi

if [[ -z "${SUPABASE_DB_URL:-}" ]]; then
  echo "[migrate] skip: SUPABASE_DB_URL not set"
  exit 0
fi

if ! command -v psql >/dev/null 2>&1; then
  echo "[migrate] skip: psql not found"
  exit 0
fi

echo "[migrate] applying ${SQL_FILE} ..."
psql "${SUPABASE_DB_URL}" -v ON_ERROR_STOP=1 -f "${SQL_FILE}"
echo "[migrate] done"
