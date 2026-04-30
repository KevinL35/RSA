import type { TaxonomyPreviewResponse } from '../dictionary/api'
import type { Dimension6Key, InsightEvidenceItem } from './dashboardTypes'
import { evidenceDisplayPlainText } from './insightResultFormatters'

function escapeHtml(s: string) {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function buildSynonymGroups(dim: Dimension6Key, preview: TaxonomyPreviewResponse | null): string[][] {
  const block = preview?.dimensions?.[dim]
  const entries = block?.entries
  if (!entries?.length) return []
  const out: string[][] = []
  for (const e of entries) {
    const can = String(e.canonical ?? '').trim()
    const als = Array.isArray(e.aliases)
      ? e.aliases.map((a) => String(a).trim()).filter(Boolean)
      : []
    const g = [...new Set([can, ...als].filter(Boolean))]
    if (g.length) out.push(g)
  }
  return out
}

function expandKeywordWithSynonyms(kw: string, groups: string[][]): string[] {
  const t = kw.trim()
  if (!t) return []
  const low = t.toLowerCase()
  for (const g of groups) {
    if (g.some((x) => x.toLowerCase() === low)) return [...g]
  }
  return [t]
}

function collectEvidenceHighlightTerms(
  ev: InsightEvidenceItem,
  groups: string[][],
  selectedKeyword: string | null,
): string[] {
  const acc = new Set<string>()
  for (const k of ev.keywords ?? []) {
    for (const x of expandKeywordWithSynonyms(String(k), groups)) {
      if (x.trim()) acc.add(x.trim())
    }
  }
  const picked = selectedKeyword?.trim()
  if (picked) {
    for (const x of expandKeywordWithSynonyms(picked, groups)) {
      if (x.trim()) acc.add(x.trim())
    }
  }
  return [...acc].sort((a, b) => b.length - a.length)
}

function highlightByMergedIntervals(escapedText: string, terms: string[]): string {
  if (!terms.length) return escapedText
  const intervals: [number, number][] = []
  for (const term of terms) {
    const piece = term.trim()
    if (!piece) continue
    const esc = escapeHtml(piece)
    if (!esc) continue
    const pattern = `(${escapeRegExp(esc)})`
    let re: RegExp
    try {
      re = new RegExp(pattern, 'giu')
    } catch {
      re = new RegExp(pattern, 'gi')
    }
    re.lastIndex = 0
    let m: RegExpExecArray | null
    while ((m = re.exec(escapedText)) !== null) {
      if (m.index === re.lastIndex) re.lastIndex++
      intervals.push([m.index, m.index + m[0].length])
    }
  }
  if (!intervals.length) return escapedText
  intervals.sort((a, b) => a[0] - b[0] || b[1] - a[1])
  const merged: [number, number][] = []
  for (const iv of intervals) {
    const last = merged[merged.length - 1]
    if (!last || iv[0] >= last[1]) merged.push([iv[0], iv[1]])
    else last[1] = Math.max(last[1], iv[1])
  }
  let out = ''
  let cur = 0
  for (const [s, e] of merged) {
    out += escapedText.slice(cur, s) + '<mark>' + escapedText.slice(s, e) + '</mark>'
    cur = e
  }
  out += escapedText.slice(cur)
  return out
}

export function highlightEvidence(
  ev: InsightEvidenceItem,
  dim: Dimension6Key,
  taxonomyPreview: TaxonomyPreviewResponse | null,
  selectedKeyword: string | null,
) {
  const raw = evidenceDisplayPlainText(ev)
  if (!raw) return ''
  const escaped = escapeHtml(raw)
  const groups = buildSynonymGroups(dim, taxonomyPreview)
  const terms = collectEvidenceHighlightTerms(ev, groups, selectedKeyword)
  return highlightByMergedIntervals(escaped, terms)
}
