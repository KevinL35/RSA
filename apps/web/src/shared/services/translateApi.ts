/**
 * TB-11：调用后端可选翻译；失败或未配置时返回 configured=false，不抛错阻断 UI。
 * TB-13：携带 X-RSA-Role。
 */
import { apiBaseUrl, getStoredRole } from './api'

export type TranslateResult = {
  configured: boolean
  translated: string | null
}

export async function translateAnalysisText(text: string, target: 'zh-CN' | 'en' = 'zh-CN'): Promise<TranslateResult> {
  const base = apiBaseUrl()
  const url = `${base}/api/v1/translate`
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        'X-RSA-Role': getStoredRole(),
      },
      body: JSON.stringify({ text, target }),
    })
    const data = (await res.json().catch(() => null)) as TranslateResult | null
    if (!res.ok || !data || typeof data.configured !== 'boolean') {
      return { configured: false, translated: null }
    }
    return {
      configured: data.configured,
      translated: typeof data.translated === 'string' ? data.translated : null,
    }
  } catch {
    return { configured: false, translated: null }
  }
}
