import { computed, ref } from 'vue'

const TOKEN_KEY = 'scaffold_demo_token'
const ROLE_KEY = 'rsa_user_role'

export type UserRole = 'admin' | 'operator' | 'readonly'

const token = ref<string>(localStorage.getItem(TOKEN_KEY) || '')
const role = ref<UserRole>((localStorage.getItem(ROLE_KEY) as UserRole) || 'readonly')

export function useAuthStore() {
  const isLogin = () => !!token.value

  const login = async (username: string, password: string, userRole: UserRole = 'admin') => {
    if (!username || !password) throw new Error('请输入账号和密码')
    token.value = `token_${Date.now()}`
    localStorage.setItem(TOKEN_KEY, token.value)
    role.value = userRole
    localStorage.setItem(ROLE_KEY, userRole)
  }

  const logout = () => {
    token.value = ''
    localStorage.removeItem(TOKEN_KEY)
    role.value = 'readonly'
    localStorage.removeItem(ROLE_KEY)
  }

  /** TB-7：失败任务「重试」——管理员与运营可操作，只读不可 */
  const canRetryInsightTasks = computed(() => role.value === 'admin' || role.value === 'operator')

  const hasRole = (allowed: UserRole | UserRole[]) => {
    const list = Array.isArray(allowed) ? allowed : [allowed]
    return list.includes(role.value)
  }

  return {
    token,
    role,
    isLogin,
    login,
    logout,
    canRetryInsightTasks,
    hasRole,
  }
}
