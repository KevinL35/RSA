/** TB-3：分析源返回结构（与 TA-1 六维 key 对齐） */

import type { InsightTaskRow } from './insight-tasks'

export type SentimentLabel = 'negative' | 'neutral' | 'positive'

export type Dimension6Key =
  | 'pros'
  | 'cons'
  | 'return_reasons'
  | 'purchase_motivation'
  | 'user_expectation'
  | 'usage_scenario'

export type HighlightSpan = {
  start: number
  end: number
  label: string
}

export type DimensionAnalysis = {
  dimension: Dimension6Key
  keywords: string[]
  evidence_quote: string | null
  highlight_spans: HighlightSpan[]
}

export type ReviewAnalysisRow = {
  review_id: string
  sentiment: {
    label: SentimentLabel
    confidence: number | null
  }
  dimensions: DimensionAnalysis[]
}

export type AnalyzeInsightTaskResponse = {
  task: InsightTaskRow
  analysis_provider_id_used: string
  review_analyses: ReviewAnalysisRow[]
}

/** TB-4：GET /api/v1/insight-tasks/{id}/analysis */

export type ReviewSnippet = {
  id: string
  raw_text: string
  title: string | null
  rating: number | null
  sku: string | null
  reviewed_at: string | null
}

export type StoredTaskAnalysisItem = {
  review_id: string
  review: ReviewSnippet | null
  sentiment: {
    label: SentimentLabel
    confidence: number | null
  }
  dimensions: DimensionAnalysis[]
  analysis_provider_id: string | null
  created_at: string
}

export type StoredTaskAnalysisResponse = {
  insight_task_id: string
  platform: string
  product_id: string
  task_status: string
  items: StoredTaskAnalysisItem[]
}

/** TB-4：GET /api/v1/analysis/by-product */

export type DimensionHitStoredRow = {
  id: string
  review_analysis_id: string
  insight_task_id: string
  review_id: string
  platform: string
  product_id: string
  dimension: Dimension6Key
  keywords: string[]
  evidence_quote: string | null
  highlight_spans: HighlightSpan[]
  created_at: string
}

export type ByProductDimensionHitsResponse = {
  platform: string
  product_id: string
  dimension_filter: string | null
  items: Array<DimensionHitStoredRow & { review: ReviewSnippet | null }>
}
