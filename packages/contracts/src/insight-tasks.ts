/** 与 Supabase `insight_tasks` 表及 GET /api/v1/insight-tasks 对齐 */

export type InsightTaskStatus =
  | 'pending'
  | 'running'
  | 'success'
  | 'failed'
  | 'cancelled'

/** Pangolin amzProductDetail 等写入 insight_tasks.product_snapshot */
export type InsightTaskProductSnapshot = {
  title?: string | null
  image_url?: string | null
  price_display?: string | null
  asin?: string | null
  source?: string | null
  fetched_at?: string | null
}

export type InsightTaskRow = {
  id: string
  platform: string
  product_id: string
  status: InsightTaskStatus
  analysis_provider_id: string | null
  /** 词典类目：general / electronics 等 */
  dictionary_vertical_id?: string | null
  /** 创建人用户名 */
  created_by?: string | null
  error_code: string | null
  error_message: string | null
  failure_stage: string | null
  created_at: string
  updated_at: string
  product_snapshot?: InsightTaskProductSnapshot | null
}

export type InsightTaskListResponse = {
  items: InsightTaskRow[]
}

export type InsightTaskCreateBody = {
  platform: string
  product_id: string
  analysis_provider_id?: string | null
  /** 默认 general；与后端词典垂直一致 */
  dictionary_vertical_id?: string
}

/** PATCH /api/v1/insight-tasks/:id — 状态迁移需符合服务端状态机 */
export type InsightTaskPatchBody = {
  status: InsightTaskStatus
  error_code?: string | null
  error_message?: string | null
  failure_stage?: string | null
}
