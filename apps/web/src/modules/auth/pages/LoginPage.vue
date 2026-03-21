<template>
  <div class="login-page">
    <div class="login-bg-orb orb-a" />
    <div class="login-bg-orb orb-b" />
    <el-card class="card" shadow="never">
      <div class="card-title">{{ t('login.title') }}</div>
      <el-form @submit.prevent="onSubmit">
        <el-form-item class="form-item">
          <el-input v-model="username" size="large" :placeholder="t('login.username')">
            <template #prefix>
              <span class="input-icon" v-html="userSvg" />
            </template>
          </el-input>
        </el-form-item>
        <el-form-item class="form-item">
          <el-input
            v-model="password"
            size="large"
            type="password"
            show-password
            :placeholder="t('login.password')"
          >
            <template #prefix>
              <span class="input-icon" v-html="passwordSvg" />
            </template>
          </el-input>
        </el-form-item>
        <el-form-item class="remember-item">
          <el-checkbox v-model="rememberPassword">{{ t('login.remember') }}</el-checkbox>
        </el-form-item>
        <el-button class="submit-btn" type="primary" size="large" :loading="loading" @click="onSubmit">
          {{ t('login.submit') }}
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { apiBaseUrl } from '../../../shared/services/api'
import { useAuthStore, type UserRole } from '../store/auth.store'

const { t } = useI18n()

const DEMO_USER = 'admin'
const DEMO_PASS = 'admin'

const REMEMBER_KEY = 'rsa_login_remember'
const CRED_KEY = 'rsa_login_credentials'

/** 进入页时同步读取，避免先闪现默认账号再被 onMounted 改掉 */
function readRememberedForm(): { username: string; password: string; remember: boolean } {
  try {
    const remember = localStorage.getItem(REMEMBER_KEY) === '1'
    if (!remember) {
      return { username: '', password: '', remember: false }
    }
    const raw = localStorage.getItem(CRED_KEY)
    if (!raw) {
      localStorage.removeItem(REMEMBER_KEY)
      return { username: '', password: '', remember: false }
    }
    const parsed = JSON.parse(raw) as { username?: string; password?: string }
    const u = typeof parsed.username === 'string' ? parsed.username : ''
    const p = typeof parsed.password === 'string' ? parsed.password : ''
    if (!u && !p) {
      localStorage.removeItem(REMEMBER_KEY)
      localStorage.removeItem(CRED_KEY)
      return { username: '', password: '', remember: false }
    }
    return { username: u, password: p, remember: true }
  } catch {
    localStorage.removeItem(REMEMBER_KEY)
    localStorage.removeItem(CRED_KEY)
    return { username: '', password: '', remember: false }
  }
}

const initialForm = readRememberedForm()
const username = ref(initialForm.username)
const password = ref(initialForm.password)
const rememberPassword = ref(initialForm.remember)
const loading = ref(false)
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const userSvg =
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024"><path fill="currentColor" d="M512 512a192 192 0 1 0 0-384 192 192 0 0 0 0 384m0 64a256 256 0 1 1 0-512 256 256 0 0 1 0 512m320 320v-96a96 96 0 0 0-96-96H288a96 96 0 0 0-96 96v96a32 32 0 1 1-64 0v-96a160 160 0 0 1 160-160h448a160 160 0 0 1 160 160v96a32 32 0 1 1-64 0"></path></svg>'
const passwordSvg =
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024"><path fill="currentColor" d="M224 448a32 32 0 0 0-32 32v384a32 32 0 0 0 32 32h576a32 32 0 0 0 32-32V480a32 32 0 0 0-32-32zm0-64h576a96 96 0 0 1 96 96v384a96 96 0 0 1-96 96H224a96 96 0 0 1-96-96V480a96 96 0 0 1 96-96"></path><path fill="currentColor" d="M512 544a32 32 0 0 1 32 32v192a32 32 0 1 1-64 0V576a32 32 0 0 1 32-32m192-160v-64a192 192 0 1 0-384 0v64zM512 64a256 256 0 0 1 256 256v128H256V320A256 256 0 0 1 512 64"></path></svg>'

type PlatformLoginJson = {
  username: string
  role: string
  menu_keys: string[]
  token: string
}

async function tryPlatformLogin(): Promise<'ok' | 'auth_fail' | 'skip'> {
  const base = apiBaseUrl()
  const url = `${base}/api/v1/platform-auth/login`
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: username.value.trim(),
        password: password.value,
      }),
    })
    if (res.ok) {
      const data = (await res.json()) as PlatformLoginJson
      const r = data.role as UserRole
      const role: UserRole =
        r === 'admin' || r === 'operator' || r === 'readonly' ? r : 'readonly'
      auth.loginWithPlatform(data.username, data.token, role, data.menu_keys ?? [])
      return 'ok'
    }
    if (res.status === 401) return 'auth_fail'
    return 'skip'
  } catch {
    return 'skip'
  }
}

function persistRememberPreference() {
  if (rememberPassword.value) {
    localStorage.setItem(REMEMBER_KEY, '1')
    localStorage.setItem(
      CRED_KEY,
      JSON.stringify({
        username: username.value,
        password: password.value,
      }),
    )
  } else {
    localStorage.removeItem(REMEMBER_KEY)
    localStorage.removeItem(CRED_KEY)
  }
}

async function onSubmit() {
  loading.value = true
  try {
    const plat = await tryPlatformLogin()
    if (plat === 'auth_fail') {
      ElMessage.error(t('login.failed'))
      return
    }
    if (plat === 'ok') {
      persistRememberPreference()
      const redir = route.query.redirect
      router.replace(typeof redir === 'string' && redir.startsWith('/') ? redir : '/insight-analysis')
      return
    }

    await auth.login(username.value, password.value, 'admin')
    if (
      username.value === DEMO_USER &&
      password.value === DEMO_PASS &&
      plat === 'skip'
    ) {
      ElMessage.warning(t('login.demoFallback'))
    }
    persistRememberPreference()
    const redir = route.query.redirect
    router.replace(typeof redir === 'string' && redir.startsWith('/') ? redir : '/insight-analysis')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : t('login.failed'))
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  position: relative;
  min-height: 100vh;
  display: grid;
  place-items: center;
  background: radial-gradient(circle at 12% 20%, #e0ecff 0%, #ecf3ff 36%, #f2f6ff 56%, #f7f9fc 100%);
  overflow: hidden;
}
.login-bg-orb {
  position: absolute;
  border-radius: 999px;
  filter: blur(1px);
}
.orb-a {
  width: 420px;
  height: 420px;
  top: -120px;
  left: -140px;
  background: radial-gradient(circle, rgba(56, 189, 248, 0.25) 0%, rgba(56, 189, 248, 0) 70%);
}
.orb-b {
  width: 460px;
  height: 460px;
  right: -140px;
  bottom: -180px;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.24) 0%, rgba(59, 130, 246, 0) 70%);
}
.card {
  width: 378px;
  padding: 14px 12px;
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.8);
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.1);
  backdrop-filter: blur(6px);
  z-index: 1;
}
.card-title {
  margin-bottom: 22px;
  font-size: 29px;
  line-height: 1.2;
  font-weight: 700;
  color: rgb(97, 98, 102);
  text-align: center;
}
.form-item {
  margin-bottom: 18px;
}
.remember-item {
  margin-top: 3px;
  margin-bottom: 18px;
}
.submit-btn {
  width: 100%;
  margin-top: 3px;
  height: 44px;
  border: none;
  background: var(--rsa-primary);
  font-size: 19px;
  font-weight: 700;
  letter-spacing: 1px;
}
.input-icon {
  width: 16px;
  height: 16px;
  display: inline-flex;
  align-items: center;
  color: #9ca3af;
}
.input-icon :deep(svg) {
  width: 16px;
  height: 16px;
  display: block;
}
:deep(.form-item .el-input__wrapper) {
  min-height: 42px;
}
:deep(.remember-item .el-checkbox__label) {
  color: #111111;
}
:deep(.remember-item .el-checkbox__input.is-checked .el-checkbox__inner) {
  background-color: var(--rsa-primary);
  border-color: var(--rsa-primary);
}
:deep(.remember-item .el-checkbox__inner:hover) {
  border-color: var(--rsa-primary);
}
</style>
