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
  ByProductDimensionHitsResponse,
  Dimension6Key,
  DimensionAnalysis,
  DimensionHitStoredRow,
  HighlightSpan,
  ReviewAnalysisRow,
  ReviewSnippet,
  SentimentLabel,
  StoredTaskAnalysisItem,
  StoredTaskAnalysisResponse,
} from './analysis'

export type {
  InsightDashboardEmptyState,
  InsightDashboardResponse,
  InsightEvidenceItem,
  PainRankItem,
} from './insight-dashboard'

export type {
  CompareConclusionCard,
  CompareKeywordEntry,
  CompareMissingReason,
  ComparePrerequisiteErrorDetail,
  CompareProductPrerequisite,
  CompareProductsResponse,
  CompareProductRef,
  CompareSentimentBucket,
} from './compare'

export type {
  InsightTaskListFiltersApplied,
  InsightTaskListWithFiltersResponse,
  InsightTaskRetryResponse,
  TaskCenterError,
  TaskCenterInsightTaskRow,
} from './task-center'
