import { apiGetJson, apiPostJson } from '../../shared/services/api'
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

export function postInsightTaskFetchReviews(taskId: string) {
  return apiPostJson<Record<string, unknown>>(`/api/v1/insight-tasks/${encodeURIComponent(taskId)}/fetch-reviews`, {})
}

export function postInsightTaskAnalyze(taskId: string) {
  return apiPostJson<Record<string, unknown>>(`/api/v1/insight-tasks/${encodeURIComponent(taskId)}/analyze`, {})
}
