


export const selectPopperOptionsNoFlip = {
  modifiers: [{ name: 'flip', enabled: false }],
} as const

export const SELECT_PLACEMENT_BOTTOM_START = 'bottom-start' as const
export const SELECT_FALLBACK_PLACEMENTS_BOTTOM = ['bottom-start', 'bottom', 'bottom-end'] as const
