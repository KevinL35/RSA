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

export type InsightAiSummaryResponse = {
  cached?: boolean
  fingerprint?: string
  ai_summary?: {
    text?: string
    model?: string
    generated_at?: string
    fingerprint?: string
  }
}

export function postInsightAiSummary(taskId: string, body?: { regenerate?: boolean }) {
  return apiPostJson<InsightAiSummaryResponse>(
    `/api/v1/insight-tasks/${encodeURIComponent(taskId)}/ai-summary`,
    { regenerate: body?.regenerate === true },
  )
}

export function postInsightTaskAnalyze(
  taskId: string,
  opts?: { forceReanalyze?: boolean },
) {
  const q =
    opts?.forceReanalyze === true
      ? '?force_reanalyze=true'
      : ''
  return apiPostJson<Record<string, unknown>>(
    `/api/v1/insight-tasks/${encodeURIComponent(taskId)}/analyze${q}`,
    {},
  )
}

export type TopicDiscoveryBody = {
  embedding_model?: string
  dry_run?: boolean
}

export type TopicDiscoveryJob = {
  id: string
  insight_task_id: string
  status: 'pending' | 'running' | 'success' | 'failed' | 'cancelled'
  embedding_model: string
  pid?: number | null
  pgid?: number | null
  batch_id?: string | null
  summary?: Record<string, unknown> | null
  error_message?: string | null
  started_at?: string | null
  finished_at?: string | null
  created_at?: string
  updated_at?: string
}

export type TopicDiscoveryStartResponse = {
  ok: boolean
  job: TopicDiscoveryJob
}


export function postTopicDiscoveryGlobal(body?: TopicDiscoveryBody) {
  return apiPostJson<TopicDiscoveryStartResponse>(`/api/v1/topic-discovery/global`, body ?? {})
}


export function fetchTopicDiscoveryGlobalLatest() {
  return apiGetJson<{ job: TopicDiscoveryJob | null }>(`/api/v1/topic-discovery/jobs/latest`)
}


export function cancelTopicDiscoveryGlobal(jobId: string) {
  return apiPostJson<TopicDiscoveryStartResponse>(
    `/api/v1/topic-discovery/jobs/${encodeURIComponent(jobId)}/cancel`,
    {},
  )
}
