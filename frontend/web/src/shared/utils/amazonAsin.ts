/**
 * 从亚马逊商品页 URL 提取 10 位 ASIN。
 * 支持 /dp/、/gp/product/、查询参数 asin=（不解析短链跳转）。
 */
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
  return /amazon\.[a-z.]{2,}\//i.test(link.trim())
}

/** 与亚马逊 ASIN 相同的字符数量（10 位字母数字）。 */
export const AMAZON_ASIN_LENGTH = 10

/**
 * 是否适合用亚马逊主图 URL 模板（列表缩略图等）。
 * 排除上传评论生成的 RSAxxxxxxx 等非 ASIN 标识。
 */
export function isLikelyAmazonAsin(id: string): boolean {
  const compact = id.trim().toUpperCase().replace(/\s+/g, '')
  if (compact.length !== AMAZON_ASIN_LENGTH || !/^[A-Z0-9]{10}$/.test(compact)) return false
  if (compact.startsWith('RSA')) return false
  return true
}

export type ResolveUploadProductIdReason = 'url_no_asin' | 'invalid_format'

const RSA_PREFIX = 'RSA'
/** RSA 后 7 位十进制数，范围 0000000–9999999（共一千万个）。 */
const RSA_NUMERIC_MOD = 10_000_000
const RSA_UPLOAD_SEQ_STORAGE_KEY = 'rsa_insight_upload_product_seq'

/** 与 ASIN 等长：RSA + 7 位数字，序号存 localStorage 递增，溢出后从 0000000 继续循环。 */
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

/**
 * 上传评论场景下的商品标识：
 * - 留空 → 自动生成 RSA + 7 位数字（如 RSA0000001，0000000–9999999 循环递增）；
 * - 亚马逊商品链接 → 提取 ASIN；
 * - 否则为 10 位字母数字：标准 ASIN 或以 RSA 开头的自定义编码。
 */
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
