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
