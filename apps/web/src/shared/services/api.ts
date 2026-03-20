/**
 * 调用 FastAPI。开发环境走 Vite proxy `/api` → 后端；生产用 VITE_API_BASE_URL。
 */
export function apiBaseUrl(): string {
  const env = import.meta.env.VITE_API_BASE_URL as string | undefined
  if (env && env.replace(/\s/g, '') !== '') {
    return env.replace(/\/$/, '')
  }
  return ''
}

export async function apiGetJson<T>(path: string): Promise<T> {
  const base = apiBaseUrl()
  const url = `${base}${path.startsWith('/') ? path : `/${path}`}`
  const res = await fetch(url, {
    headers: { Accept: 'application/json' },
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
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `HTTP ${res.status}`)
  }
  return (await res.json()) as T
}
