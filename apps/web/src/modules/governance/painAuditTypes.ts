/** 词典审核列表行（前端态；与 TA-9 候选 / TA-10 决策可对齐） */

export type PainAuditRowKind = 'new_discovery' | 'existing' | 'rejected'

export type SixDimension =
  | 'pros'
  | 'cons'
  | 'return_reasons'
  | 'purchase_motivation'
  | 'user_expectation'
  | 'usage_scenario'

export interface PainAuditRow {
  id: string
  kind: PainAuditRowKind
  /** 规范词 / 关键词 */
  canonical: string
  synonyms: string[]
  vertical_id: string
  dimension_6way?: SixDimension
  batch_id?: string
  source_topic_id?: string
  quality_score?: number
  created_at?: string
  updated_at?: string
}

export const SIX_DIMENSIONS: SixDimension[] = [
  'pros',
  'cons',
  'return_reasons',
  'purchase_motivation',
  'user_expectation',
  'usage_scenario',
]
