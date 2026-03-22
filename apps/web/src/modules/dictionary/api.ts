import { apiDeleteJson, apiGetJson, apiPatchJson, apiPostJson } from '../../shared/services/api'

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

export type ApproveDictionaryEntryBody = {
  vertical_ids: string[]
  dimension_6way: string
  canonical: string
  aliases: string[]
  batch_id?: string | null
  source_topic_id?: string | null
  /** 对应 Supabase dictionary_review_queue.id，通过后标记 approved */
  review_queue_id?: string | null
}

export type ApproveDictionaryEntryResponse = {
  ok: boolean
  vertical_ids?: string[]
  dimension_6way?: string
  canonical?: string
  updated?: Array<{ vertical_id: string; path: string; version: string; entry_count: number }>
  hint?: string
}

export function postDictionaryApproveEntry(body: ApproveDictionaryEntryBody) {
  return apiPostJson<ApproveDictionaryEntryResponse>('/api/v1/dictionary/approve-entry', body)
}

export type DictionaryReviewQueueItem = {
  id: string
  kind: 'new_discovery' | 'existing'
  canonical: string
  synonyms: string[]
  vertical_id: string
  dimension_6way?: string | null
  batch_id?: string | null
  source_topic_id?: string | null
  quality_score?: number | null
}

export type PatchDictionaryReviewQueueBody = {
  canonical: string
  synonyms: string[]
}

export type PatchDictionaryReviewQueueResponse = {
  ok: boolean
  item: DictionaryReviewQueueItem
}

export function patchDictionaryReviewQueue(id: string, body: PatchDictionaryReviewQueueBody) {
  const q = encodeURIComponent(id)
  return apiPatchJson<PatchDictionaryReviewQueueResponse>(`/api/v1/dictionary/review-queue/${q}`, body)
}

export function deleteDictionaryReviewQueue(id: string) {
  const q = encodeURIComponent(id)
  return apiDeleteJson<{ ok: boolean; id: string }>(`/api/v1/dictionary/review-queue/${q}`)
}

export type DictionaryReviewQueueResponse = {
  items: DictionaryReviewQueueItem[]
}

export function fetchDictionaryReviewQueue() {
  return apiGetJson<DictionaryReviewQueueResponse>('/api/v1/dictionary/review-queue')
}
