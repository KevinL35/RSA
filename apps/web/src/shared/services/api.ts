/**
 * 调用 FastAPI。开发环境走 Vite proxy `/api` → 后端；生产用 VITE_API_BASE_URL。
 * TB-13：所有请求携带 `X-RSA-Role`，与 `auth.store` / localStorage `rsa_user_role` 一致。
 */
export function apiBaseUrl(): string {
  const env = import.meta.env.VITE_API_BASE_URL as string | undefined
  if (env && env.replace(/\s/g, '') !== '') {
    return env.replace(/\/$/, '')
  }
  return ''
}

const ROLE_KEY = 'rsa_user_role'

export type ApiRole = 'admin' | 'operator' | 'readonly'

export function getStoredRole(): ApiRole {
  try {
    const r = localStorage.getItem(ROLE_KEY)
    if (r === 'admin' || r === 'operator' || r === 'readonly') return r
  } catch {
    /* ignore */
  }
  return 'readonly'
}

function authHeaders(extra?: Record<string, string>): Record<string, string> {
  return {
    Accept: 'application/json',
    'X-RSA-Role': getStoredRole(),
    ...extra,
  }
}

export async function apiGetJson<T>(path: string): Promise<T> {
  const base = apiBaseUrl()
  const url = `${base}${path.startsWith('/') ? path : `/${path}`}`
  const res = await fetch(url, {
    headers: authHeaders(),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `HTTP ${res.status}`)
  }
  return (await res.json()) as T
}

export async function apiPostJson<T>(path: string, body: unknown): Promise<T> {
  const base = apiBaseUrl()
  const url = `${base}${path.startsWith('/') ? path : `/${path}`}`
  const res = await fetch(url, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `HTTP ${res.status}`)
  }
  return (await res.json()) as T
}
