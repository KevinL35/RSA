/**
 * TB-9：GET /api/v1/compare/products
 * TB-10：HTTP 400 时 FastAPI 将 ComparePrerequisiteErrorDetail 放在 response JSON 的 `detail` 内
 */

export type CompareMissingReason = 'no_success_task' | 'empty_analysis'

export type CompareProductPrerequisite = {
  platform: string
  product_id: string
  insight_task_id: string | null
}

export type ComparePrerequisiteErrorDetail = {
  code: 'MISSING_INSIGHT_DATA'
  /** 英文摘要，便于日志与旧客户端 */
  message: string
  messages: { zh_CN: string; en: string }
  guidance: { zh_CN: string; en: string }
  next_step: { route: string; label_zh: string; label_en: string }
  missing: { a: boolean; b: boolean }
  reasons: { a: CompareMissingReason | null; b: CompareMissingReason | null }
  products: { a: CompareProductPrerequisite; b: CompareProductPrerequisite }
}

export type CompareSentimentBucket = {
  negative: number
  neutral: number
  positive: number
}

export type CompareProductRef = {
  platform: string
  product_id: string
  insight_task_id: string
}

export type CompareKeywordEntry = {
  keyword: string
  count: number
}

export type CompareConclusionCard = {
  kind: 'sentiment' | 'dimension' | 'keyword' | 'summary'
  title: string
  detail: string
}

export type CompareProductsResponse = {
  product_a: CompareProductRef
  product_b: CompareProductRef
  sentiment: {
    a: CompareSentimentBucket
    b: CompareSentimentBucket
    delta: CompareSentimentBucket
  }
  dimensions: {
    a: Record<string, number>
    b: Record<string, number>
    delta: Record<string, number>
  }
  keywords: {
    a: CompareKeywordEntry[]
    b: CompareKeywordEntry[]
    relative_more_in_a: CompareKeywordEntry[]
    relative_more_in_b: CompareKeywordEntry[]
  }
  conclusion_cards: CompareConclusionCard[]
}
