export type TaskCenterError = {
  stage: string | null
  code: string | null
  message: string | null
}

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
  status: string
  analysis_provider_id: string | null
  dictionary_vertical_id?: string | null
  
  created_by?: string | null
  error_code: string | null
  error_message: string | null
  failure_stage: string | null
  created_at: string
  updated_at: string
  
  product_snapshot?: InsightTaskProductSnapshot | null
  
  ai_summary?: { text?: string; model?: string; generated_at?: string; fingerprint?: string } | null
  
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
