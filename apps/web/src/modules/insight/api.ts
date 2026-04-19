import { apiGetJson, apiPostFormData, apiPostJson } from '../../shared/services/api'

export type InsightTaskReviewRow = {
  id: string
  platform?: string
  product_id?: string
  external_review_id?: string | null
  raw_text: string
  title?: string | null
  rating?: number | null
  sku?: string | null
  reviewed_at?: string | null
  lang?: string | null
  extra?: Record<string, unknown> | null
  created_at?: string
}

export type InsightTaskReviewsResponse = {
  insight_task_id: string
  platform: string
  product_id: string
  task_status: string
  count: number
  items: InsightTaskReviewRow[]
}
import type { InsightTaskRow } from '../tasks/types'
import type { InsightTaskCreateBody } from './types'
import type { InsightDashboardResponse } from './dashboardTypes'

export type DashboardQuery = {
  evidence_limit?: number
  evidence_offset?: number
  evidence_dimension?: string
}

export function fetchInsightDashboard(taskId: string, params?: DashboardQuery) {
  const sp = new URLSearchParams()
  if (params?.evidence_limit != null) sp.set('evidence_limit', String(params.evidence_limit))
  if (params?.evidence_offset != null) sp.set('evidence_offset', String(params.evidence_offset))
  if (params?.evidence_dimension) sp.set('evidence_dimension', params.evidence_dimension)
  const q = sp.toString()
  return apiGetJson<InsightDashboardResponse>(
    `/api/v1/insight-tasks/${encodeURIComponent(taskId)}/dashboard${q ? `?${q}` : ''}`,
  )
}

export function createInsightTask(body: InsightTaskCreateBody) {
  return apiPostJson<InsightTaskRow>('/api/v1/insight-tasks', body)
}

export function fetchInsightTaskReviews(taskId: string, limit = 20000) {
  return apiGetJson<InsightTaskReviewsResponse>(
    `/api/v1/insight-tasks/${encodeURIComponent(taskId)}/reviews?limit=${limit}`,
  )
}

export type FetchReviewsResponse = {
  reviews_inserted?: number
  task?: unknown
}

export function postInsightTaskFetchReviews(taskId: string) {
  return apiPostJson<FetchReviewsResponse>(
    `/api/v1/insight-tasks/${encodeURIComponent(taskId)}/fetch-reviews`,
    {},
  )
}

export function postInsightTaskImportReviews(taskId: string, file: File) {
  const fd = new FormData()
  fd.append('file', file)
  return apiPostFormData<FetchReviewsResponse>(
    `/api/v1/insight-tasks/${encodeURIComponent(taskId)}/import-reviews`,
    fd,
  )
}

export function postInsightTaskAnalyze(taskId: string) {
  return apiPostJson<Record<string, unknown>>(`/api/v1/insight-tasks/${encodeURIComponent(taskId)}/analyze`, {})
}

export type TopicDiscoveryBody = {
  embedding_model?: string
  dry_run?: boolean
}

export function postInsightTaskTopicDiscovery(taskId: string, body?: TopicDiscoveryBody) {
  return apiPostJson<Record<string, unknown>>(
    `/api/v1/insight-tasks/${encodeURIComponent(taskId)}/topic-discovery`,
    body ?? {},
  )
}

/**
 * 与 postInsightTaskTopicDiscovery 等价，但支持 AbortController：
 * 前端可调 controller.abort() 取消等待；服务端子进程不受此影响（仍会跑完）。
 */
export async function postInsightTaskTopicDiscoveryWithSignal(
  taskId: string,
  body: TopicDiscoveryBody | undefined,
  signal: AbortSignal,
): Promise<Record<string, unknown>> {
  const { apiBaseUrl, getStoredRole } = await import('../../shared/services/api')
  const { getStoredUsername } = await import('../auth/store/auth.store')
  const base = apiBaseUrl()
  const path = `/api/v1/insight-tasks/${encodeURIComponent(taskId)}/topic-discovery`
  const url = `${base}${path}`
  const u = getStoredUsername()
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      'X-RSA-Role': getStoredRole(),
      ...(u ? { 'X-RSA-Username': u } : {}),
    },
    body: JSON.stringify(body ?? {}),
    signal,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `HTTP ${res.status}`)
  }
  return (await res.json()) as Record<string, unknown>
}
