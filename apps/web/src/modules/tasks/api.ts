import { apiGetJson, apiPostJson } from '../../shared/services/api'
import type { InsightTaskListResponse, InsightTaskRetryResponse } from './types'

export type TaskListQuery = {
  status?: string
  created_after?: string
  created_before?: string
  limit?: number
}

export function fetchInsightTasks(params?: TaskListQuery) {
  const sp = new URLSearchParams()
  if (params?.status) sp.set('status', params.status)
  if (params?.created_after) sp.set('created_after', params.created_after)
  if (params?.created_before) sp.set('created_before', params.created_before)
  if (params?.limit != null) sp.set('limit', String(params.limit))
  const q = sp.toString()
  return apiGetJson<InsightTaskListResponse>(`/api/v1/insight-tasks${q ? `?${q}` : ''}`)
}

export function postInsightTaskRetry(taskId: string) {
  return apiPostJson<InsightTaskRetryResponse>(`/api/v1/insight-tasks/${taskId}/retry`, {})
}
