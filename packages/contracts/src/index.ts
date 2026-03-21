export type ApiEnvelope<T> = {
  code: string
  message: string
  data: T
}

export type {
  InsightTaskCreateBody,
  InsightTaskListResponse,
  InsightTaskPatchBody,
  InsightTaskRow,
  InsightTaskStatus,
} from './insight-tasks'

export type { FetchReviewsResponse, ReviewRow } from './reviews'

export type {
  AnalyzeInsightTaskResponse,
  Dimension6Key,
  DimensionAnalysis,
  HighlightSpan,
  ReviewAnalysisRow,
  SentimentLabel,
} from './analysis'
