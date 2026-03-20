import { ref } from 'vue'

const TOKEN_KEY = 'scaffold_demo_token'
const token = ref<string>(localStorage.getItem(TOKEN_KEY) || '')

export function useAuthStore() {
  const isLogin = () => !!token.value

  const login = async (username: string, password: string) => {
    // TODO: 替换成你的真实登录 API
    if (!username || !password) {
      throw new Error('请输入账号和密码')
    }
    token.value = `token_${Date.now()}`
    localStorage.setItem(TOKEN_KEY, token.value)
  }

  const logout = () => {
    token.value = ''
    localStorage.removeItem(TOKEN_KEY)
  }

  return { token, isLogin, login, logout }
}
