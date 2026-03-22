/**
 * 浏览器端导出 .xlsx（依赖 sheetjs / xlsx）。
 */
export async function downloadReviewsExcel(
  filename: string,
  items: Record<string, unknown>[],
  columns: readonly string[],
  sheetName = 'Reviews',
): Promise<void> {
  const XLSX = await import('xlsx')
  const rows = items.map((item) => {
    const o: Record<string, unknown> = {}
    for (const c of columns) {
      o[c] = item[c] ?? ''
    }
    return o
  })
  const ws = XLSX.utils.json_to_sheet(rows, { header: [...columns] })
  const wb = XLSX.utils.book_new()
  const safeSheet = sheetName.slice(0, 31).replace(/[:\\/?*[\]]/g, '_')
  XLSX.utils.book_append_sheet(wb, ws, safeSheet || 'Reviews')
  const name = filename.toLowerCase().endsWith('.xlsx') ? filename : `${filename}.xlsx`
  XLSX.writeFile(wb, name)
}

/** 评论导入模板表头（与后端 import-reviews 解析一致）。 */
export const REVIEW_IMPORT_TEMPLATE_COLUMNS = ['时间', '评论'] as const

/** 下载空模板（含表头与一行示例，可删除后填写）。 */
export async function downloadReviewImportTemplate(): Promise<void> {
  const cols = [...REVIEW_IMPORT_TEMPLATE_COLUMNS]
  await downloadReviewsExcel(
    '评论导入模板.xlsx',
    [
      { 时间: '', 评论: '' },
      { 时间: '2026-01-15', 评论: '示例：可删除本行后填写真实评论' },
    ],
    cols,
  )
}

/** 词典 Excel 列（与后端 import_dictionary_excel 解析一致）。 */
export const DICTIONARY_IMPORT_COLUMNS = ['六维维度', '规范词', '同义词', '权重', '优先级'] as const

export async function downloadDictionaryImportTemplate(): Promise<void> {
  const cols = [...DICTIONARY_IMPORT_COLUMNS]
  await downloadReviewsExcel(
    '词典导入模板.xlsx',
    [
      {
        六维维度: 'cons',
        规范词: 'battery life',
        同义词: 'dies fast; poor battery',
        权重: 1,
        优先级: 70,
      },
    ],
    cols,
    'Dictionary',
  )
}

export type TaxonomyPreviewLike = {
  dimension_order: string[]
  dimensions: Record<
    string,
    {
      entries?: Array<{
        canonical?: string | null
        aliases?: unknown
        weight?: number | null
        priority?: number | null
      }>
    }
  >
}

/** 将 taxonomy-preview 展平为词典 Excel 行（中文表头）。 */
export function flattenTaxonomyPreviewForExcel(preview: TaxonomyPreviewLike): Record<string, unknown>[] {
  const rows: Record<string, unknown>[] = []
  for (const dim of preview.dimension_order) {
    const entries = preview.dimensions[dim]?.entries ?? []
    for (const e of entries) {
      const aliases = Array.isArray(e.aliases)
        ? e.aliases.map((x) => String(x).trim()).filter(Boolean)
        : []
      rows.push({
        六维维度: dim,
        规范词: String(e.canonical ?? '').trim(),
        同义词: aliases.join('；'),
        权重: e.weight ?? 1,
        优先级: e.priority ?? 50,
      })
    }
  }
  return rows
}

export async function downloadDictionaryAsExcel(
  verticalLabel: string,
  preview: TaxonomyPreviewLike,
): Promise<void> {
  const safe = verticalLabel.replace(/[/\\?*[\]:]/g, '_').slice(0, 40) || 'dictionary'
  const rows = flattenTaxonomyPreviewForExcel(preview)
  await downloadReviewsExcel(
    `词典导出_${safe}.xlsx`,
    rows,
    [...DICTIONARY_IMPORT_COLUMNS],
    'Dictionary',
  )
}
