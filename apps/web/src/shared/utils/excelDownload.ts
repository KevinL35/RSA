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
