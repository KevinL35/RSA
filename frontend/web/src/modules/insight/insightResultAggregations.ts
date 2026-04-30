import type { Dimension6Key, InsightDashboardResponse, PainRankItem } from './dashboardTypes'

export const painRankingDimensions: Dimension6Key[] = ['cons', 'return_reasons']

const WORDCLOUD_PALETTES: Record<Dimension6Key, string[]> = {
  pros: ['#047857', '#059669', '#10b981', '#34d399', '#6ee7b7'],
  cons: ['#b45309', '#d97706', '#f59e0b', '#fbbf24', '#fcd34d'],
  return_reasons: ['#be123c', '#e11d48', '#f43f5e', '#fb7185', '#fda4af'],
  purchase_motivation: ['#1d4ed8', '#2563eb', '#3b82f6', '#60a5fa', '#93c5fd'],
  user_expectation: ['#0e7490', '#0891b2', '#06b6d4', '#22d3ee', '#67e8f9'],
  usage_scenario: ['#6d28d9', '#7c3aed', '#8b5cf6', '#a78bfa', '#c4b5fd'],
}

function hashKeywordHue(keyword: string): number {
  let h = 0
  for (let i = 0; i < keyword.length; i++) h = (h * 31 + keyword.charCodeAt(i)) >>> 0
  return h
}

export function pickWordCloudColor(keyword: string, dim: Dimension6Key): string {
  const palette = WORDCLOUD_PALETTES[dim]
  if (!palette?.length) return '#047857'
  return palette[hashKeywordHue(keyword) % palette.length]!
}

export function primaryDimensionFromRankDims(dims: string[], dimensionOrder: Dimension6Key[]): Dimension6Key {
  for (const d of dimensionOrder) {
    if (dims.includes(d)) return d
  }
  const first = dims[0]
  if (first && dimensionOrder.includes(first as Dimension6Key)) return first as Dimension6Key
  return 'pros'
}

export function primaryDimensionForPainKeyword(
  keyword: string,
  dashboard: InsightDashboardResponse | null,
  dimensionOrder: Dimension6Key[],
): Dimension6Key {
  if (!dashboard?.pain_ranking?.length) return 'pros'
  const low = keyword.trim().toLowerCase()
  const row = dashboard.pain_ranking.find((p) => p.keyword.trim().toLowerCase() === low)
  if (!row?.dimensions?.length) return 'pros'
  return primaryDimensionFromRankDims(row.dimensions, dimensionOrder)
}

export function painForDimension(dim: Dimension6Key, list: PainRankItem[]) {
  return list.filter((p) => p.dimensions.includes(dim))
}

export function buildCardRows(
  dim: Dimension6Key,
  dashboard: InsightDashboardResponse | null,
): { label: string; count: number; pct: number }[] {
  if (!dashboard) return []
  const counter = new Map<string, number>()
  for (const ev of dashboard.evidence.items) {
    if (String(ev.dimension) !== dim) continue
    const kws = ev.keywords
    if (!Array.isArray(kws) || kws.length === 0) continue
    const seen = new Set<string>()
    for (const raw of kws) {
      const kw = String(raw).trim().toLowerCase()
      if (!kw || seen.has(kw)) continue
      seen.add(kw)
      counter.set(kw, (counter.get(kw) || 0) + 1)
    }
  }
  const denom = dashboard.evidence.items.length || 1
  return [...counter.entries()]
    .map(([keyword, count]) => ({
      label: keyword,
      count,
      pct: Math.round((count / denom) * 100),
    }))
    .sort((a, b) => b.count - a.count)
}

export function primaryPainRankingDimension(dims: string[]): Dimension6Key {
  for (const d of painRankingDimensions) {
    if (dims.includes(d)) return d
  }
  return 'cons'
}

export function trendForKeyword(kw: string) {
  let h = 0
  for (let i = 0; i < kw.length; i++) h = (h + kw.charCodeAt(i) * (i + 1)) % 3
  return h === 0 ? '↑' : h === 1 ? '→' : '↓'
}

export function keywordsAggregatedForDimension(
  dim: Dimension6Key,
  dashboard: InsightDashboardResponse | null,
): { keyword: string; count: number }[] {
  if (!dashboard?.pain_ranking?.length) return []
  const map = new Map<string, number>()
  for (const p of dashboard.pain_ranking) {
    if (!p.dimensions.includes(dim)) continue
    const k = p.keyword.trim()
    if (!k) continue
    map.set(k, (map.get(k) || 0) + p.count)
  }
  return [...map.entries()]
    .map(([keyword, count]) => ({ keyword, count }))
    .sort((a, b) => b.count - a.count)
}

export function keywordsAggregatedAllDimensions(
  dashboard: InsightDashboardResponse | null,
): { keyword: string; count: number }[] {
  if (!dashboard?.pain_ranking?.length) return []
  return dashboard.pain_ranking
    .map((p) => ({ keyword: p.keyword.trim(), count: p.count }))
    .filter((x) => x.keyword)
    .sort((a, b) => b.count - a.count)
}
