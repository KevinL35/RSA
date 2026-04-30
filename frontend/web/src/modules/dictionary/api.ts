import {
  apiDeleteJson,
  apiGetJson,
  apiPatchJson,
  apiPostFormData,
  apiPostJson,
} from '../../shared/services/api'

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

export type DictionaryTaxonomyAgentReviewBody = {
  vertical_id: string
  dimension_6way: string
}

export type DictionaryTaxonomyAgentReviewResponse = {
  ok: boolean
  vertical_id: string
  dimension_6way: string
  total: number
  rejected_entries: number
  rejected_aliases: number
  queued: number
}

export function postDictionaryTaxonomyAgentReview(body: DictionaryTaxonomyAgentReviewBody) {
  return apiPostJson<DictionaryTaxonomyAgentReviewResponse>('/api/v1/dictionary/taxonomy/agent-review', body)
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
  kind: 'new_discovery' | 'existing' | 'rejected'
  canonical: string
  synonyms: string[]
  vertical_id: string
  dimension_6way?: string | null
  batch_id?: string | null
  source_topic_id?: string | null
  quality_score?: number | null
  created_at?: string | null
  updated_at?: string | null
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

export type PostDictionaryReviewQueueBody = {
  canonical: string
  synonyms: string[]
  /** 省略时使用平台默认类目（与后端 DEFAULT_VERTICAL_ID 一致） */
  vertical_id?: string | null
}

export type PostDictionaryReviewQueueResponse = {
  ok: boolean
  merged?: boolean
  item: DictionaryReviewQueueItem
}

export function postDictionaryReviewQueue(body: PostDictionaryReviewQueueBody) {
  return apiPostJson<PostDictionaryReviewQueueResponse>('/api/v1/dictionary/review-queue', body)
}

export type DictionaryAgentReviewResultItem = {
  id: string
  canonical?: string
  before_dimension_6way?: string | null
  suggested_dimension_6way?: string | null
}

export type DictionaryAgentReviewResponse = {
  ok: boolean
  total: number
  reviewed: number
  updated: number
  items: DictionaryAgentReviewResultItem[]
}

export function postDictionaryAgentReview(limit = 50) {
  return apiPostJson<DictionaryAgentReviewResponse>(
    `/api/v1/dictionary/review-queue/agent-review?limit=${encodeURIComponent(String(limit))}`,
    {},
  )
}

export type DictionarySmartMergeBody = {
  vertical_id: string
  dimension_6way: string
  queue_ids: string[]
}

export type DictionarySmartMergeResponse = {
  ok: boolean
  vertical_id?: string
  dimension_6way?: string
  merge_keeps?: number
  merge_drops_deleted?: number
  updates?: number
  rejects?: number
  /** 本次请求里带给模型的「已入库词条」条数（同词典同六维） */
  existing_dictionary_context_sent?: number
  existing_dictionary_context_total?: number
  existing_dictionary_context_truncated?: boolean
}

export function postDictionarySmartMerge(body: DictionarySmartMergeBody) {
  return apiPostJson<DictionarySmartMergeResponse>('/api/v1/dictionary/review-queue/smart-merge', body)
}

export type DictionaryReviewRecordsResponse = {
  items: Array<{
    review_queue_id?: string | null
    canonical?: string | null
    synonyms?: string[]
    agent_reviewed_at?: string | null
    suggested_dimension_6way?: string | null
    approved_at?: string | null
    approved_dimension_6way?: string | null
    vertical_ids?: string[]
    target_dictionary_table?: string | null
  }>
  limit: number
}

export function fetchDictionaryReviewRecords(limit = 100) {
  return apiGetJson<DictionaryReviewRecordsResponse>(
    `/api/v1/dictionary/review-records?limit=${encodeURIComponent(String(limit))}`,
  )
}

export type DictionaryReviewMergeLogsResponse = {
  items: Array<{
    at?: string | null
    action: 'approved' | 'rejected'
    review_queue_id?: string | null
    canonical?: string | null
    vertical_id?: string | null
    dimension_6way?: string | null
    source?: string | null
    reason_zh?: string | null
  }>
  limit: number
}

export function fetchDictionaryReviewMergeLogs(limit = 100) {
  return apiGetJson<DictionaryReviewMergeLogsResponse>(
    `/api/v1/dictionary/review-merge-logs?limit=${encodeURIComponent(String(limit))}`,
  )
}

export type DictionaryImportExcelResponse = {
  ok: boolean
  imported: number
  warnings?: string[]
  updated?: { vertical_id: string; path: string; version: string; entry_count: number }
  hint?: string
}

export function postDictionaryImportExcel(verticalId: string, file: File) {
  const fd = new FormData()
  fd.append('vertical_id', verticalId)
  fd.append('file', file)
  return apiPostFormData<DictionaryImportExcelResponse>('/api/v1/dictionary/import-excel', fd)
}
