import { computed, ref } from 'vue'

const TOKEN_KEY = 'scaffold_demo_token'
const ROLE_KEY = 'rsa_user_role'
const MENU_KEYS_KEY = 'rsa_menu_keys'
const USERNAME_KEY = 'rsa_login_username'
const USE_PLATFORM_AUTH_KEY = 'rsa_use_platform_auth'

export type UserRole = 'admin' | 'operator' | 'readonly'

const token = ref<string>(localStorage.getItem(TOKEN_KEY) || '')
const role = ref<UserRole>((localStorage.getItem(ROLE_KEY) as UserRole) || 'readonly')
const menuKeys = ref<string[]>(readMenuKeysFromStorage())
const displayUsername = ref<string>(localStorage.getItem(USERNAME_KEY) || '')

function readMenuKeysFromStorage(): string[] {
  try {
    const raw = localStorage.getItem(MENU_KEYS_KEY)
    if (!raw) return []
    const p = JSON.parse(raw) as unknown
    return Array.isArray(p) ? p.map((x) => String(x)) : []
  } catch {
    return []
  }
}

export function getStoredMenuKeys(): string[] {
  try {
    const raw = localStorage.getItem(MENU_KEYS_KEY)
    if (!raw) return []
    const p = JSON.parse(raw) as unknown
    return Array.isArray(p) ? p.map((x) => String(x)) : []
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

export function useAuthStore() {
  const isLogin = () => !!token.value

  /** 本地演示登录（未走平台用户库） */
  const login = async (username: string, password: string, userRole: UserRole = 'admin') => {
    if (!username || !password) throw new Error('请输入账号和密码')
    token.value = `token_${Date.now()}`
    localStorage.setItem(TOKEN_KEY, token.value)
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
    localStorage.setItem(TOKEN_KEY, accessToken)
    role.value = userRole
    localStorage.setItem(ROLE_KEY, userRole)
    menuKeys.value = [...keys]
    localStorage.setItem(MENU_KEYS_KEY, JSON.stringify(keys))
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
