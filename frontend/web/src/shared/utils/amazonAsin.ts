



export function extractAsinFromAmazonUrl(link: string): string | null {
  const s = link.trim()
  if (!s) return null
  const m1 = s.match(/\/(?:dp|gp\/product)\/([A-Z0-9]{10})(?:\/|[?#]|$)/i)
  if (m1) return m1[1].toUpperCase()
  const m2 = s.match(/[?&]asin=([A-Z0-9]{10})(?:&|[#]|$)/i)
  if (m2) return m2[1].toUpperCase()
  return null
}

export function looksLikeAmazonProductUrl(link: string): boolean {
  return /amazon\.[a-z.]{2,}/i.test(link)
}


export const AMAZON_ASIN_LENGTH = 10





export function isLikelyAmazonAsin(id: string): boolean {
  const compact = id.trim().toUpperCase().replace(/\s+/g, '')
  if (compact.length !== AMAZON_ASIN_LENGTH || !/^[A-Z0-9]{10}$/.test(compact)) return false
  if (compact.startsWith('RSA')) return false
  return true
}

export type ResolveUploadProductIdReason = 'url_no_asin' | 'invalid_format'

const RSA_PREFIX = 'RSA'

const RSA_NUMERIC_MOD = 10_000_000
const RSA_UPLOAD_SEQ_STORAGE_KEY = 'rsa_insight_upload_product_seq'


export function generateUploadReviewProductId(): string {
  try {
    const raw = localStorage.getItem(RSA_UPLOAD_SEQ_STORAGE_KEY)
    let next = raw != null ? parseInt(raw, 10) : 1
    if (!Number.isFinite(next)) next = 1
    next = ((next % RSA_NUMERIC_MOD) + RSA_NUMERIC_MOD) % RSA_NUMERIC_MOD
    const id = `${RSA_PREFIX}${String(next).padStart(7, '0')}`
    const following = next >= RSA_NUMERIC_MOD - 1 ? 0 : next + 1
    localStorage.setItem(RSA_UPLOAD_SEQ_STORAGE_KEY, String(following))
    return id
  } catch {
    const fallback = Math.floor(Math.random() * RSA_NUMERIC_MOD)
    return `${RSA_PREFIX}${String(fallback).padStart(7, '0')}`
  }
}







export function resolveProductIdForUploadReviews(input: string):
  | { ok: true; productId: string }
  | { ok: false; reason: ResolveUploadProductIdReason } {
  const trimmed = input.trim()
  if (!trimmed) {
    return { ok: true, productId: generateUploadReviewProductId() }
  }
  if (looksLikeAmazonProductUrl(trimmed)) {
    const fromUrl = extractAsinFromAmazonUrl(trimmed)
    if (!fromUrl) {
      return { ok: false, reason: 'url_no_asin' }
    }
    return { ok: true, productId: fromUrl }
  }
  const compact = trimmed.replace(/\s+/g, '').toUpperCase()
  if (compact.length !== AMAZON_ASIN_LENGTH || !/^[A-Z0-9]{10}$/.test(compact)) {
    return { ok: false, reason: 'invalid_format' }
  }
  return { ok: true, productId: compact }
}
