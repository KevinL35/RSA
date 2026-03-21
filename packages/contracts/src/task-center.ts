/** TB-6：任务列表筛选与重试 */

import type { InsightTaskRow } from './insight-tasks'

export type TaskCenterError = {
  stage: string | null
  code: string | null
  message: string | null
}

export type TaskCenterInsightTaskRow = InsightTaskRow & {
  error: TaskCenterError | null
}

export type InsightTaskListFiltersApplied = {
  task_type: string
  status: string[] | null
  created_after: string | null
  created_before: string | null
  limit: number
}

export type InsightTaskListWithFiltersResponse = {
  items: TaskCenterInsightTaskRow[]
  filters_applied: InsightTaskListFiltersApplied
}

export type InsightTaskRetryResponse = {
  task: TaskCenterInsightTaskRow
  idempotent: boolean
  action: 'none' | 'reset_to_pending'
  message: string
}
