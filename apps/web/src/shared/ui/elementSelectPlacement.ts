/**
 * Element Plus el-select：固定优先向下展开，禁用 Popper flip（避免靠底/弹窗内翻到上方）。
 */
export const selectPopperOptionsNoFlip = {
  modifiers: [{ name: 'flip', enabled: false }],
} as const

export const SELECT_PLACEMENT_BOTTOM_START = 'bottom-start' as const
export const SELECT_FALLBACK_PLACEMENTS_BOTTOM = ['bottom-start', 'bottom', 'bottom-end'] as const
