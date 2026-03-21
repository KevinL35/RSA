export type TaskCenterError = {
  stage: string | null
  code: string | null
  message: string | null
}

export type InsightTaskRow = {
  id: string
  platform: string
  product_id: string
  status: string
  analysis_provider_id: string | null
  dictionary_vertical_id?: string | null
  /** 创建人用户名（Supabase insight_tasks.created_by） */
  created_by?: string | null
  error_code: string | null
  error_message: string | null
  failure_stage: string | null
  created_at: string
  updated_at: string
  /** TB-6：失败任务结构化错误；非失败为 null */
  error?: TaskCenterError | null
}

export type InsightTaskListFiltersApplied = {
  task_type: string
  status: string[] | null
  created_after: string | null
  created_before: string | null
  limit: number
}

export type InsightTaskListResponse = {
  items: InsightTaskRow[]
  filters_applied?: InsightTaskListFiltersApplied
}

export type InsightTaskRetryResponse = {
  task: InsightTaskRow
  idempotent: boolean
  action: 'none' | 'reset_to_pending'
  message: string
}
