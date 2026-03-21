import { apiGetJson, apiPostJson } from '../../shared/services/api'

export type DictionaryVerticalItem = {
  id: string
  label_zh: string
  label_en: string
  description_zh: string
  description_en: string
}

export type DictionaryVerticalsResponse = {
  items: DictionaryVerticalItem[]
  dimension_order: string[]
}

export type TaxonomyPreviewEntry = {
  dimension_6way?: string
  canonical?: string
  aliases?: string[]
  weight?: number
  priority?: number
}

export type TaxonomyPreviewDimensionBlock = {
  key: string
  count: number
  entries: TaxonomyPreviewEntry[]
}

export type TaxonomyPreviewResponse = {
  vertical_id: string
  entry_count: number
  dimension_order: string[]
  dimensions: Record<string, TaxonomyPreviewDimensionBlock>
}

export function fetchDictionaryVerticals() {
  return apiGetJson<DictionaryVerticalsResponse>('/api/v1/dictionary/verticals')
}

export function fetchTaxonomyPreview(verticalId: string) {
  const q = new URLSearchParams({ vertical_id: verticalId })
  return apiGetJson<TaxonomyPreviewResponse>(`/api/v1/dictionary/taxonomy-preview?${q}`)
}

export type RejectSynonymBody = {
  vertical_id: string
  dimension_6way: string
  canonical: string
  alias: string
}

export type RejectSynonymResponse = {
  ok: boolean
  queued?: boolean
  vertical_id?: string
  dimension_6way?: string
  canonical?: string
  alias?: string
}

export function postDictionaryRejectSynonym(body: RejectSynonymBody) {
  return apiPostJson<RejectSynonymResponse>('/api/v1/dictionary/reject-synonym', body)
}
