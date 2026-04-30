import { getStoredUsername } from '../../modules/auth/store/auth.store'





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
    
  }
  return 'readonly'
}

function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const u = getStoredUsername()
  return {
    Accept: 'application/json',
    'X-RSA-Role': getStoredRole(),
    ...(u ? { 'X-RSA-Username': u } : {}),
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

export async function apiPostFormData<T>(path: string, formData: FormData): Promise<T> {
  const base = apiBaseUrl()
  const url = `${base}${path.startsWith('/') ? path : `/${path}`}`
  const u = getStoredUsername()
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'X-RSA-Role': getStoredRole(),
      ...(u ? { 'X-RSA-Username': u } : {}),
    },
    body: formData,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `HTTP ${res.status}`)
  }
  return (await res.json()) as T
}


export async function apiPostJsonPublic<T>(path: string, body: unknown): Promise<T> {
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

export async function apiPatchJson<T>(path: string, body: unknown): Promise<T> {
  const base = apiBaseUrl()
  const url = `${base}${path.startsWith('/') ? path : `/${path}`}`
  const res = await fetch(url, {
    method: 'PATCH',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `HTTP ${res.status}`)
  }
  const ct = res.headers.get('content-type') || ''
  if (!ct.includes('application/json')) {
    return {} as T
  }
  const text = await res.text()
  if (!text.trim()) {
    return {} as T
  }
  return JSON.parse(text) as T
}

export async function apiDeleteJson<T>(path: string): Promise<T> {
  const base = apiBaseUrl()
  const url = `${base}${path.startsWith('/') ? path : `/${path}`}`
  const res = await fetch(url, {
    method: 'DELETE',
    headers: authHeaders(),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `HTTP ${res.status}`)
  }
  const ct = res.headers.get('content-type') || ''
  if (!ct.includes('application/json')) {
    return {} as T
  }
  const text = await res.text()
  if (!text.trim()) {
    return {} as T
  }
  return JSON.parse(text) as T
}
