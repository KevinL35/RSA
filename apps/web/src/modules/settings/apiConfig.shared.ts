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
    model: 'rsa-platform-v1',
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

const defaultTranslateRows = (): ApiConfigRow[] => [
  {
    id: 'tr_1',
    name: 'LibreTranslate 兼容端点',
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
  const list = rows as ApiConfigRow[]
  if (hasBuiltinInsight(list)) return list
  return [...defaultInsightRows(), ...list.filter((r) => r.id !== 'ins_builtin')]
}

function normalizeAgentRows(rows: unknown): ApiConfigRow[] {
  if (!Array.isArray(rows) || rows.length === 0) return defaultAgentRows()
  return rows as ApiConfigRow[]
}

function normalizeTranslateRows(rows: unknown): ApiConfigRow[] {
  if (!Array.isArray(rows) || rows.length === 0) return defaultTranslateRows()
  return rows as ApiConfigRow[]
}

type Bundle = {
  insight: ApiConfigRow[]
  agent: ApiConfigRow[]
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
export const translateApiConfigRows = ref<ApiConfigRow[]>(initial.translate)

function persistAll() {
  persistBundle({
    insight: insightApiConfigRows.value,
    agent: agentApiConfigRows.value,
    translate: translateApiConfigRows.value,
  })
}

watch(insightApiConfigRows, persistAll, { deep: true })
watch(agentApiConfigRows, persistAll, { deep: true })
watch(translateApiConfigRows, persistAll, { deep: true })
