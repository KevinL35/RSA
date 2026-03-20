import { apiGetJson } from '../../shared/services/api'
import type { InsightTaskListResponse } from './types'

export function fetchInsightTasks() {
  return apiGetJson<InsightTaskListResponse>('/api/v1/insight-tasks')
}
