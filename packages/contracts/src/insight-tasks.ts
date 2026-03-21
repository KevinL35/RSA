/** 与 Supabase `insight_tasks` 表及 GET /api/v1/insight-tasks 对齐 */

export type InsightTaskStatus =
  | 'pending'
  | 'running'
  | 'success'
  | 'failed'
  | 'cancelled'

export type InsightTaskRow = {
  id: string
  platform: string
  product_id: string
  status: InsightTaskStatus
  analysis_provider_id: string | null
  error_code: string | null
  error_message: string | null
  failure_stage: string | null
  created_at: string
  updated_at: string
}

export type InsightTaskListResponse = {
  items: InsightTaskRow[]
}

export type InsightTaskCreateBody = {
  platform: string
  product_id: string
  analysis_provider_id?: string | null
}

/** PATCH /api/v1/insight-tasks/:id — 状态迁移需符合服务端状态机 */
export type InsightTaskPatchBody = {
  status: InsightTaskStatus
  error_code?: string | null
  error_message?: string | null
  failure_stage?: string | null
}
