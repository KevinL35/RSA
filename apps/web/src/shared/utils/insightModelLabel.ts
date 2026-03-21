import type { ApiConfigRow } from '../../modules/settings/apiConfig.shared'

type TFn = (key: string, values?: Record<string, string>) => string

export type InsightModelFormatInput = Pick<ApiConfigRow, 'name' | 'model'> & { builtin?: boolean }

/** 列表 / 下拉 / 结果页统一：「名称：模型」；无模型时仅名称 */
export function formatInsightModelLine(row: InsightModelFormatInput, t: TFn): string {
  const name = row.builtin ? t('settings.insightBuiltinModelName') : row.name
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
  const name = cfg.builtin ? t('settings.insightBuiltinModelName') : cfg.name?.trim()
  return name || providerId
}
