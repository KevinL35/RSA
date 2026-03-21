/** 与表 public.reviews 及抓取结果接口对齐 */

import type { InsightTaskRow } from './insight-tasks'

export type ReviewRow = {
  id: string
  insight_task_id: string
  platform: string
  product_id: string
  external_review_id: string | null
  raw_text: string
  title: string | null
  rating: number | null
  sku: string | null
  reviewed_at: string | null
  lang: string | null
  extra: Record<string, unknown> | null
  created_at: string
}

export type FetchReviewsResponse = {
  task: InsightTaskRow
  reviews_inserted: number
}
