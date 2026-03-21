/** TB-5：GET /api/v1/insight-tasks/{id}/dashboard */

import type { Dimension6Key } from './analysis'

export type InsightDashboardEmptyState = {
  code: 'TASK_NOT_READY' | 'NO_ANALYSIS_DATA' | string
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
  dimension: Dimension6Key | string
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

export type InsightDashboardResponse = {
  insight_task_id: string
  platform: string
  product_id: string
  task_status: string
  analysis_provider_id?: string | null
  /** 任务最近更新时间（分析完成后通常与完成时刻接近），ISO 8601 */
  analyzed_at?: string | null
  empty_state: InsightDashboardEmptyState | null
  dimension_counts: Partial<Record<Dimension6Key, number>>
  pain_ranking: PainRankItem[]
  evidence: {
    items: InsightEvidenceItem[]
    total: number
    limit: number
    offset: number
  }
  /** 按评论 reviewed_at 日期聚合的条数，用于时间趋势 */
  review_timeseries?: ReviewTimeseriesPoint[]
}
