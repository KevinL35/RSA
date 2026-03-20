export type InsightTaskRow = {
  id: string
  platform: string
  product_id: string
  status: string
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
