/** 路由 path → 所需侧栏菜单 key（与 menu.config 一致） */
export function pathRequiredMenuKey(path: string): string | null {
  if (path.startsWith('/insight-analysis')) return 'insight'
  if (path.startsWith('/compare-analysis')) return 'compare'
  if (path.startsWith('/pain-audit')) return 'pain-audit'
  if (path.startsWith('/dictionary')) return 'dictionary'
  if (path.startsWith('/system-settings/api-config')) return 'api-config'
  if (path.startsWith('/system-settings/account-permissions')) return 'account-permissions'
  return null
}

const KEY_ORDER: { key: string; path: string }[] = [
  { key: 'insight', path: '/insight-analysis' },
  { key: 'compare', path: '/compare-analysis' },
  { key: 'pain-audit', path: '/pain-audit' },
  { key: 'dictionary', path: '/dictionary' },
  { key: 'api-config', path: '/system-settings/api-config' },
  { key: 'account-permissions', path: '/system-settings/account-permissions' },
]

export function firstAllowedPath(menuKeys: string[]): string {
  const set = new Set(menuKeys)
  for (const { key, path } of KEY_ORDER) {
    if (set.has(key)) return path
  }
  return '/insight-analysis'
}
