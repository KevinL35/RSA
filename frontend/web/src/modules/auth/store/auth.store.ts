import { computed, ref } from 'vue'

const TOKEN_KEY = 'scaffold_demo_token'
const ROLE_KEY = 'rsa_user_role'
const MENU_KEYS_KEY = 'rsa_menu_keys'
const USERNAME_KEY = 'rsa_login_username'
const USE_PLATFORM_AUTH_KEY = 'rsa_use_platform_auth'

export type UserRole = 'admin' | 'operator' | 'readonly'

/** 与 backend/platform-api platform_users.constants ADMIN_MENU_KEYS 一致 */
const ADMIN_MENU_KEYS = new Set([
  'smart-mining',
  'dictionary',
  'api-config',
  'audit-log',
  'account-permissions',
])

function normalizeMenuKey(k: string): string {
  return k.trim()
}

export function deriveRoleFromMenuKeys(keys: string[]): UserRole {
  const ks = new Set(keys.map((k) => normalizeMenuKey(k)).filter(Boolean))
  for (const k of ks) {
    if (ADMIN_MENU_KEYS.has(k)) return 'admin'
  }
  if (ks.has('insight')) return 'operator'
  return 'readonly'
}

const token = ref<string>('')
const role = ref<UserRole>((localStorage.getItem(ROLE_KEY) as UserRole) || 'readonly')
const menuKeys = ref<string[]>(readMenuKeysFromStorage())
const displayUsername = ref<string>(localStorage.getItem(USERNAME_KEY) || '')

// 不做自动登录：启动时清理旧 token，刷新后需重新登录
localStorage.removeItem(TOKEN_KEY)
if (!token.value) {
  role.value = 'readonly'
  menuKeys.value = []
  localStorage.removeItem(ROLE_KEY)
  localStorage.removeItem(MENU_KEYS_KEY)
  localStorage.removeItem(USE_PLATFORM_AUTH_KEY)
}

function readMenuKeysFromStorage(): string[] {
  try {
    const raw = localStorage.getItem(MENU_KEYS_KEY)
    if (!raw) return []
    const p = JSON.parse(raw) as unknown
    return Array.isArray(p) ? p.map((x) => normalizeMenuKey(String(x))) : []
  } catch {
    return []
  }
}

export function getStoredMenuKeys(): string[] {
  try {
    const raw = localStorage.getItem(MENU_KEYS_KEY)
    if (!raw) return []
    const p = JSON.parse(raw) as unknown
    return Array.isArray(p) ? p.map((x) => normalizeMenuKey(String(x))) : []
  } catch {
    return []
  }
}

export function isPlatformMenuAuth(): boolean {
  try {
    return localStorage.getItem(USE_PLATFORM_AUTH_KEY) === '1'
  } catch {
    return false
  }
}

/** 当前登录用户名（平台登录或演示登录写入），供创建人展示与 API 请求头 */
export function getStoredUsername(): string {
  try {
    const s = localStorage.getItem(USERNAME_KEY)
    return s ? s.trim() : ''
  } catch {
    return ''
  }
}

/**
 * 在「账号权限」中保存 menu_keys 后同步到当前会话，侧栏会立即更新（无需重新登录）。
 */
export function syncPlatformMenusFromRemote(keys: string[], usernameNext?: string) {
  if (!isPlatformMenuAuth()) return
  const next = keys.map((k) => normalizeMenuKey(k))
  menuKeys.value = next
  localStorage.setItem(MENU_KEYS_KEY, JSON.stringify(next))
  const nextRole = deriveRoleFromMenuKeys(next)
  role.value = nextRole
  localStorage.setItem(ROLE_KEY, nextRole)
  if (usernameNext !== undefined && usernameNext.trim()) {
    displayUsername.value = usernameNext.trim()
    localStorage.setItem(USERNAME_KEY, usernameNext.trim())
  }
}

export function useAuthStore() {
  const isLogin = () => !!token.value

  /** 本地演示登录（未走平台用户库） */
  const login = async (username: string, password: string, userRole: UserRole = 'admin') => {
    if (!username || !password) throw new Error('请输入账号和密码')
    token.value = `token_${Date.now()}`
    role.value = userRole
    localStorage.setItem(ROLE_KEY, userRole)
    localStorage.removeItem(MENU_KEYS_KEY)
    localStorage.removeItem(USE_PLATFORM_AUTH_KEY)
    menuKeys.value = []
    displayUsername.value = username
    localStorage.setItem(USERNAME_KEY, username)
  }

  const loginWithPlatform = (
    username: string,
    accessToken: string,
    userRole: UserRole,
    keys: string[],
  ) => {
    token.value = accessToken
    role.value = userRole
    localStorage.setItem(ROLE_KEY, userRole)
    const normalized = keys.map((k) => normalizeMenuKey(k))
    menuKeys.value = normalized
    localStorage.setItem(MENU_KEYS_KEY, JSON.stringify(normalized))
    localStorage.setItem(USE_PLATFORM_AUTH_KEY, '1')
    displayUsername.value = username
    localStorage.setItem(USERNAME_KEY, username)
  }

  const logout = () => {
    token.value = ''
    localStorage.removeItem(TOKEN_KEY)
    role.value = 'readonly'
    localStorage.removeItem(ROLE_KEY)
    menuKeys.value = []
    localStorage.removeItem(MENU_KEYS_KEY)
    localStorage.removeItem(USE_PLATFORM_AUTH_KEY)
    displayUsername.value = ''
    localStorage.removeItem(USERNAME_KEY)
  }

  const canRetryInsightTasks = computed(() => role.value === 'admin' || role.value === 'operator')

  const hasRole = (allowed: UserRole | UserRole[]) => {
    const list = Array.isArray(allowed) ? allowed : [allowed]
    return list.includes(role.value)
  }

  return {
    token,
    role,
    menuKeys,
    displayUsername,
    isLogin,
    login,
    loginWithPlatform,
    logout,
    canRetryInsightTasks,
    hasRole,
  }
}
