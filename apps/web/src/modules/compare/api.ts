import {
  apiBaseUrl,
  apiDeleteJson,
  apiGetJson,
  apiPostJson,
  getStoredRole,
} from '../../shared/services/api'
import type { ComparePrerequisiteErrorDetail, CompareProductsResponse } from './types'

export type CompareQuery = {
  platform_a: string
  product_id_a: string
  platform_b: string
  product_id_b: string
}

export class ComparePrerequisiteError extends Error {
  readonly detail: ComparePrerequisiteErrorDetail

  constructor(detail: ComparePrerequisiteErrorDetail) {
    super(detail.message)
    this.name = 'ComparePrerequisiteError'
    this.detail = detail
  }
}

/**
 * TB-10：400 时抛出 ComparePrerequisiteError（body.detail 为 ComparePrerequisiteErrorDetail）。
 */
export async function fetchCompareProducts(q: CompareQuery): Promise<CompareProductsResponse> {
  const sp = new URLSearchParams({
    platform_a: q.platform_a.trim(),
    product_id_a: q.product_id_a.trim(),
    platform_b: q.platform_b.trim(),
    product_id_b: q.product_id_b.trim(),
  })
  const base = apiBaseUrl()
  const url = `${base}/api/v1/compare/products?${sp.toString()}`
  const res = await fetch(url, {
    headers: { Accept: 'application/json', 'X-RSA-Role': getStoredRole() },
  })
  const data = (await res.json().catch(() => null)) as
    | { detail?: ComparePrerequisiteErrorDetail | string }
    | CompareProductsResponse
    | null

  if (!res.ok) {
    const detail =
      data && typeof data === 'object' && 'detail' in data ? data.detail : undefined
    if (
      res.status === 400 &&
      detail &&
      typeof detail === 'object' &&
      (detail as ComparePrerequisiteErrorDetail).code === 'MISSING_INSIGHT_DATA'
    ) {
      throw new ComparePrerequisiteError(detail as ComparePrerequisiteErrorDetail)
    }
    const msg =
      typeof detail === 'string'
        ? detail
        : JSON.stringify(data ?? {})
    throw new Error(msg || `HTTP ${res.status}`)
  }
  return data as CompareProductsResponse
}

export type CompareRunListItem = {
  id: string
  platform_a: string
  product_id_a: string
  platform_b: string
  product_id_b: string
  creator: string
  created_at: string
  model_id: string | null
  model_label: string | null
  status: 'success' | 'failed'
  error_message: string | null
}

export type CompareRunDetail = CompareRunListItem & {
  result: CompareProductsResponse | null
}

export async function fetchCompareRunsList(limit = 200): Promise<{ items: CompareRunListItem[] }> {
  return apiGetJson<{ items: CompareRunListItem[] }>(`/api/v1/compare/runs?limit=${limit}`)
}

export async function fetchCompareRunDetail(id: string): Promise<CompareRunDetail> {
  return apiGetJson<CompareRunDetail>(`/api/v1/compare/runs/${encodeURIComponent(id)}`)
}

export async function createCompareRun(body: {
  platform_a: string
  product_id_a: string
  platform_b: string
  product_id_b: string
  model_id?: string | null
  model_label?: string | null
}): Promise<{ id: string; status: 'success' | 'failed'; error_message: string | null }> {
  return apiPostJson(`/api/v1/compare/runs`, body)
}

export async function deleteCompareRunRemote(id: string): Promise<{ ok: boolean }> {
  return apiDeleteJson<{ ok: boolean }>(`/api/v1/compare/runs/${encodeURIComponent(id)}`)
}
