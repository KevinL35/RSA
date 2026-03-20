import { apiPostJson } from '../../shared/services/api'
import type { InsightTaskCreateBody } from './types'

export function createInsightTask(payload: InsightTaskCreateBody) {
  return apiPostJson('/api/v1/insight-tasks', payload)
}
