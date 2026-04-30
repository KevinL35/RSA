import type { InsightEvidenceItem } from './dashboardTypes'

export function formatLocalDateTime(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso.replace('T', ' ').slice(0, 19)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

export function isHeaderImageUrl(s: string): boolean {
  const x = s.trim().toLowerCase()
  return x.startsWith('https://') || x.startsWith('http://') || x.startsWith('data:image/')
}

export function evidenceDisplayPlainText(ev: InsightEvidenceItem): string {
  const rawFull = typeof ev.review?.raw_text === 'string' ? ev.review.raw_text : ''
  const quote = typeof ev.evidence_quote === 'string' ? ev.evidence_quote : ''
  return (rawFull.trim() || quote.trim()) || ''
}

export function formatReviewDateTime(ev: InsightEvidenceItem): string {
  const raw = ev.review?.reviewed_at
  if (typeof raw !== 'string' || !raw.trim()) return '—'
  const s = raw.trim()
  const day = s.slice(0, 10)
  if (/^\d{4}-\d{2}-\d{2}$/.test(day)) return day
  const t = s.split('T')[0] ?? ''
  return /^\d{4}-\d{2}-\d{2}$/.test(t) ? t : '—'
}
