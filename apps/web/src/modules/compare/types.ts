/** 对比分析 API 相关类型（TB-9/TB-10） */

export type CompareMissingReason = 'no_success_task' | 'empty_analysis'

export type CompareProductPrerequisite = {
  platform: string
  product_id: string
  insight_task_id: string | null
}

export type ComparePrerequisiteErrorDetail = {
  code: 'MISSING_INSIGHT_DATA'
  message: string
  messages: { zh_CN: string; en: string }
  guidance: { zh_CN: string; en: string }
  next_step: { route: string; label_zh: string; label_en: string }
  missing: { a: boolean; b: boolean }
  reasons: { a: CompareMissingReason | null; b: CompareMissingReason | null }
  products: { a: CompareProductPrerequisite; b: CompareProductPrerequisite }
}

export type CompareProductsResponse = {
  product_a: { platform: string; product_id: string; insight_task_id: string }
  product_b: { platform: string; product_id: string; insight_task_id: string }
  sentiment: {
    a: { negative: number; neutral: number; positive: number }
    b: { negative: number; neutral: number; positive: number }
    delta: { negative: number; neutral: number; positive: number }
  }
  conclusion_cards: { kind: string; title: string; detail: string }[]
}
