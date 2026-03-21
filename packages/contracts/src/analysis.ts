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
