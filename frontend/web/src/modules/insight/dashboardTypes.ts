

export type Dimension6Key =
  | 'pros'
  | 'cons'
  | 'return_reasons'
  | 'purchase_motivation'
  | 'user_expectation'
  | 'usage_scenario'

export type InsightDashboardEmptyState = {
  code: string
  message: string
  hint?: string
}

export type PainRankItem = {
  keyword: string
  count: number
  dimensions: string[]
}

export type InsightEvidenceItem = {
  id: string
  dimension: string
  keywords: string[]
  evidence_quote: string | null
  highlight_spans: unknown[]
  review_id: string
  insight_task_id: string | null
  review: Record<string, unknown> | null
}

export type ReviewTimeseriesPoint = {
  date: string
  count: number
}


export type InsightTaskProductSnapshot = {
  title?: string | null
  image_url?: string | null
  price_display?: string | null
  asin?: string | null
  source?: string | null
  fetched_at?: string | null
}


export type InsightAiSummaryStored = {
  text?: string
  model?: string
  generated_at?: string
  fingerprint?: string
}

export type InsightDashboardResponse = {
  insight_task_id: string
  platform: string
  product_id: string
  task_status: string
  
  review_total_count?: number
  
  matched_review_count?: number
  analysis_provider_id?: string | null
  analyzed_at?: string | null
  product_snapshot?: InsightTaskProductSnapshot | null
  dictionary_vertical_id?: string | null
  empty_state: InsightDashboardEmptyState | null
  dimension_counts: Partial<Record<Dimension6Key, number>>
  pain_ranking: PainRankItem[]
  evidence: {
    items: InsightEvidenceItem[]
    total: number
    limit: number
    offset: number
  }
  review_timeseries?: ReviewTimeseriesPoint[]
  ai_summary?: InsightAiSummaryStored | null
}
