

export type SmartMiningRowKind = 'new_discovery' | 'existing' | 'rejected'

export type SixDimension =
  | 'pros'
  | 'cons'
  | 'return_reasons'
  | 'purchase_motivation'
  | 'user_expectation'
  | 'usage_scenario'

export interface SmartMiningRow {
  id: string
  kind: SmartMiningRowKind
  
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
