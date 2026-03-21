import { ref, watch } from 'vue'

const STORAGE_KEY = 'rsa_settings_api_config_v1'
const LEGACY_INSIGHT_KEY = 'rsa_settings_insight_models_v1'

export type ApiConfigRow = {
  id: string
  name: string
  baseUrl: string
  apiKey: string
  model: string
  createdAt: string
  builtin?: boolean
}

/** @deprecated use ApiConfigRow */
export type InsightApiConfigRow = ApiConfigRow

const defaultInsightRows = (): ApiConfigRow[] => [
  {
    id: 'ins_builtin',
    builtin: true,
    name: '',
    baseUrl: 'https://api.rsa.internal/v1/insight',
    apiKey: '',
    model: 'rsa-v1',
    createdAt: '2026-01-01 00:00:00',
  },
]

const defaultAgentRows = (): ApiConfigRow[] => [
  {
    id: 'ag_1',
    name: '对比结论 Agent（占位）',
    baseUrl: 'https://api.deepseek.com/v1',
    apiKey: '',
    model: 'deepseek-chat',
    createdAt: '2026-03-05 14:02:09',
  },
]

const defaultReviewFetchRows = (): ApiConfigRow[] => [
  {
    id: 'rf_pangolin',
    builtin: true,
    name: '',
    baseUrl: 'https://scrapeapi.pangolinfo.com',
    apiKey: '',
    model: 'amzReviewV2',
    createdAt: '2026-03-10 09:30:00',
  },
]

const defaultTranslateRows = (): ApiConfigRow[] => [
  {
    id: 'tr_default',
    builtin: true,
    name: '',
    baseUrl: 'https://libretranslate.com/translate',
    apiKey: '',
    model: '',
    createdAt: '2026-03-10 09:30:00',
  },
]

function hasBuiltinInsight(rows: ApiConfigRow[]) {
  return rows.some((r) => r.builtin === true && r.id === 'ins_builtin')
}

function normalizeInsightRows(rows: unknown): ApiConfigRow[] {
  if (!Array.isArray(rows) || rows.length === 0) return defaultInsightRows()
  const list = (rows as ApiConfigRow[]).map((r) =>
    r.id === 'ins_builtin' && r.builtin && r.model === 'rsa-platform-v1'
      ? { ...r, model: 'rsa-v1' }
      : r,
  )
  if (hasBuiltinInsight(list)) return list
  return [...defaultInsightRows(), ...list.filter((r) => r.id !== 'ins_builtin')]
}

function normalizeAgentRows(rows: unknown): ApiConfigRow[] {
  if (!Array.isArray(rows) || rows.length === 0) return defaultAgentRows()
  return rows as ApiConfigRow[]
}

function hasBuiltinReviewFetch(rows: ApiConfigRow[]) {
  return rows.some((r) => r.builtin === true && r.id === 'rf_pangolin')
}

function hasBuiltinTranslate(rows: ApiConfigRow[]) {
  return rows.some((r) => r.builtin === true && r.id === 'tr_default')
}

function normalizeTranslateRows(rows: unknown): ApiConfigRow[] {
  if (!Array.isArray(rows) || rows.length === 0) return defaultTranslateRows()
  const list = rows as ApiConfigRow[]
  if (hasBuiltinTranslate(list)) return list
  return [...defaultTranslateRows(), ...list.filter((r) => r.id !== 'tr_default')]
}

function normalizeReviewFetchRows(rows: unknown): ApiConfigRow[] {
  if (!Array.isArray(rows) || rows.length === 0) return defaultReviewFetchRows()
  const list = rows as ApiConfigRow[]
  if (hasBuiltinReviewFetch(list)) return list
  return [...defaultReviewFetchRows(), ...list.filter((r) => r.id !== 'rf_pangolin')]
}

type Bundle = {
  insight: ApiConfigRow[]
  agent: ApiConfigRow[]
  reviewFetch: ApiConfigRow[]
  translate: ApiConfigRow[]
}

function loadBundle(): Bundle {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const p = JSON.parse(raw) as Record<string, unknown>
      if (p && typeof p === 'object' && 'insight' in p) {
        return {
          insight: normalizeInsightRows(p.insight),
          agent: normalizeAgentRows(p.agent),
          reviewFetch: normalizeReviewFetchRows(p.reviewFetch),
          translate: normalizeTranslateRows(p.translate),
        }
      }
    }
  } catch {
    /* ignore */
  }

  try {
    const leg = localStorage.getItem(LEGACY_INSIGHT_KEY)
    if (leg) {
      const parsed = JSON.parse(leg) as unknown
      if (Array.isArray(parsed) && parsed.length > 0) {
        const bundle: Bundle = {
          insight: normalizeInsightRows(parsed),
          agent: defaultAgentRows(),
          reviewFetch: defaultReviewFetchRows(),
          translate: defaultTranslateRows(),
        }
        persistBundle(bundle)
        try {
          localStorage.removeItem(LEGACY_INSIGHT_KEY)
        } catch {
          /* ignore */
        }
        return bundle
      }
    }
  } catch {
    /* ignore */
  }

  return {
    insight: defaultInsightRows(),
    agent: defaultAgentRows(),
    reviewFetch: defaultReviewFetchRows(),
    translate: defaultTranslateRows(),
  }
}

function persistBundle(b: Bundle) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(b))
  } catch {
    /* ignore */
  }
}

const initial = loadBundle()

export const insightApiConfigRows = ref<ApiConfigRow[]>(initial.insight)
export const agentApiConfigRows = ref<ApiConfigRow[]>(initial.agent)
export const reviewFetchApiConfigRows = ref<ApiConfigRow[]>(initial.reviewFetch)
export const translateApiConfigRows = ref<ApiConfigRow[]>(initial.translate)

function persistAll() {
  persistBundle({
    insight: insightApiConfigRows.value,
    agent: agentApiConfigRows.value,
    reviewFetch: reviewFetchApiConfigRows.value,
    translate: translateApiConfigRows.value,
  })
}

watch(insightApiConfigRows, persistAll, { deep: true })
watch(agentApiConfigRows, persistAll, { deep: true })
watch(reviewFetchApiConfigRows, persistAll, { deep: true })
watch(translateApiConfigRows, persistAll, { deep: true })
