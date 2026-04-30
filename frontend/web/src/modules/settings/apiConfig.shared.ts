import { ref, watch } from 'vue'

const STORAGE_KEY = 'rsa_settings_api_config_v1'

export type ApiConfigRow = {
  id: string
  name: string
  baseUrl: string
  apiKey: string
  model: string
  createdAt: string
  builtin?: boolean
}

const defaultAgentRows = (): ApiConfigRow[] => [
  {
    id: 'ag_1',
    name: '对比结论 Agent（占位）',
    baseUrl: 'https://api.deepseek.com/v1',
    apiKey: '',
    model: 'deepseek-reasoner',
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
  agent: ApiConfigRow[]
  reviewFetch: ApiConfigRow[]
  translate: ApiConfigRow[]
}

function loadBundle(): Bundle {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const p = JSON.parse(raw) as Record<string, unknown>
      if (p && typeof p === 'object') {
        return {
          agent: normalizeAgentRows(p.agent),
          reviewFetch: normalizeReviewFetchRows(p.reviewFetch),
          translate: normalizeTranslateRows(p.translate),
        }
      }
    }
  } catch {
    
  }

  return {
    agent: defaultAgentRows(),
    reviewFetch: defaultReviewFetchRows(),
    translate: defaultTranslateRows(),
  }
}

function persistBundle(b: Bundle) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(b))
  } catch {
    
  }
}

const initial = loadBundle()

export const agentApiConfigRows = ref<ApiConfigRow[]>(initial.agent)
export const reviewFetchApiConfigRows = ref<ApiConfigRow[]>(initial.reviewFetch)
export const translateApiConfigRows = ref<ApiConfigRow[]>(initial.translate)

function persistAll() {
  persistBundle({
    agent: agentApiConfigRows.value,
    reviewFetch: reviewFetchApiConfigRows.value,
    translate: translateApiConfigRows.value,
  })
}

watch(agentApiConfigRows, persistAll, { deep: true })
watch(reviewFetchApiConfigRows, persistAll, { deep: true })
watch(translateApiConfigRows, persistAll, { deep: true })
