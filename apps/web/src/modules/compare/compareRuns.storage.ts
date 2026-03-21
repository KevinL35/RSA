import type { CompareProductsResponse } from './types'

const STORAGE_KEY = 'rsa_compare_runs_v1'

export type StoredCompareRun = {
  id: string
  platform_a: string
  product_id_a: string
  platform_b: string
  product_id_b: string
  creator: string
  created_at_iso: string
  /** 提交时选用的接口配置 id，便于重新生成 */
  model_id?: string
  model_label: string
  status: 'success' | 'failed'
  error_message?: string
  result?: CompareProductsResponse
}

export function loadCompareRuns(): StoredCompareRun[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const v = JSON.parse(raw) as unknown
    return Array.isArray(v) ? (v as StoredCompareRun[]) : []
  } catch {
    return []
  }
}

export function saveCompareRuns(runs: StoredCompareRun[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(runs))
}

export function upsertCompareRun(run: StoredCompareRun) {
  const runs = loadCompareRuns()
  const i = runs.findIndex((x) => x.id === run.id)
  if (i >= 0) runs[i] = run
  else runs.unshift(run)
  saveCompareRuns(runs)
}

export function getCompareRunById(id: string): StoredCompareRun | undefined {
  return loadCompareRuns().find((r) => r.id === id)
}
