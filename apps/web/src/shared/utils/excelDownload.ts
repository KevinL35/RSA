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
