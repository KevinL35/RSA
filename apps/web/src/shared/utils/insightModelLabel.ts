import type { ApiConfigRow } from '../../modules/settings/apiConfig.shared'

type TFn = (key: string, values?: Record<string, string>) => string

export type InsightModelFormatInput = Pick<ApiConfigRow, 'name' | 'model'> & {
  builtin?: boolean
  id?: string
}

/** 内置行若填写了 name（如 DeepSeek）则展示该名称，否则展示「平台自研」文案 */
export function insightModelDisplayName(row: InsightModelFormatInput, t: TFn): string {
  const n = row.name?.trim()
  if (row.builtin && n) return n
  if (row.builtin) return t('settings.insightBuiltinModelName')
  return n || ''
}

/** 列表 / 下拉 / 结果页统一：「名称：模型」；无模型时仅名称 */
export function formatInsightModelLine(row: InsightModelFormatInput, t: TFn): string {
  const name = insightModelDisplayName(row, t)
  const m = row.model?.trim()
  if (m) return t('insight.insightModelLine', { name, model: m })
  return name
}

export function formatInsightModelLineByProviderId(
  providerId: string | null,
  rows: ApiConfigRow[],
  t: TFn,
): string {
  if (!providerId) return t('insight.defaultAnalysisProvider')
  const cfg = rows.find((r) => r.id === providerId)
  return cfg ? formatInsightModelLine(cfg, t) : providerId
}

/** 列表紧凑展示：有模型 id 时只显示模型；否则显示配置名称或回退 id */
export function formatInsightModelShort(
  providerId: string | null,
  rows: ApiConfigRow[],
  t: TFn,
): string {
  if (!providerId) return t('insight.defaultAnalysisProvider')
  const cfg = rows.find((r) => r.id === providerId)
  if (!cfg) return providerId
  const m = cfg.model?.trim()
  if (m) return m
  const name = insightModelDisplayName(cfg, t)
  return name || providerId
}
