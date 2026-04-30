<template>
  <div>
    <section class="config-block config-block--intro">
      <div class="intro-head">
        <h2 class="page-title">{{ t('settings.apiTitle') }}</h2>
        <el-select
          v-model="locale"
          class="system-select"
          teleported
          placement="bottom-start"
          :fallback-placements="selectFallbackPlacementsBottom"
          :popper-options="selectPopperOptionsNoFlip"
          @change="onSystemLangChange"
        >
          <el-option :label="t('settings.langEnglish')" value="en" />
          <el-option :label="t('settings.langZhCN')" value="zh-CN" />
        </el-select>
      </div>
      <p class="intro-text">{{ t('settings.apiDesc') }}</p>
    </section>

    <section class="config-block" v-loading="usersLoading">
      <div class="block-head">
        <div>
          <h3 class="block-title">{{ t('settings.accTitle') }}</h3>
          <p class="block-subtitle">{{ t('settings.accDesc') }}</p>
        </div>
        <el-button type="primary" @click="openAddUser">
          {{ t('settings.accAdd') }}
        </el-button>
      </div>
      <el-alert
        v-if="usersLoadError"
        type="error"
        :title="usersLoadError"
        :closable="false"
        class="alert-below-header"
      />
      <el-table :data="userRows" stripe class="block-table">
        <el-table-column prop="username" :label="t('settings.accColUser')" min-width="140" />
        <el-table-column :label="t('settings.accColStatus')" width="140">
          <template #default="{ row }">
            <el-tag v-if="isCurrentLoginUser(row)" type="primary" size="small">
              {{ t('settings.accCurrentLogin') }}
            </el-tag>
            <el-tag v-else :type="row.status === 'active' ? 'success' : 'info'" size="small">
              {{ row.status === 'active' ? t('settings.accStatusActive') : t('settings.accStatusDisabled') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('settings.accColCreated')" width="188">
          <template #default="{ row }">
            {{ formatUserTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column :label="t('settings.accColActions')" width="168" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="openEditUser(row)">{{ t('settings.accEdit') }}</el-button>
            <el-button type="danger" link @click="confirmDeleteUser(row)">{{ t('settings.accDelete') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-dialog
      v-model="userAddVisible"
      :title="t('settings.accDialogAdd')"
      width="480px"
      destroy-on-close
      align-center
      @closed="resetAddUserForm"
    >
      <el-form label-position="top">
        <el-form-item :label="t('settings.accFormUser')" required>
          <el-input v-model="userAddForm.username" clearable autocomplete="off" />
        </el-form-item>
        <el-form-item :label="t('settings.accFormPassword')" required>
          <el-input
            v-model="userAddForm.password"
            type="password"
            show-password
            autocomplete="new-password"
          />
        </el-form-item>
        <el-form-item :label="t('settings.accFormMenus')" required>
          <el-checkbox-group v-model="userAddForm.menu_keys" class="menu-check-group">
            <el-checkbox v-for="opt in menuOptions" :key="opt.key" :value="opt.key">
              {{ t(opt.labelKey) }}
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="userAddVisible = false">{{ t('settings.accCancel') }}</el-button>
        <el-button type="primary" :loading="userSaving" @click="submitAddUser">{{ t('settings.accConfirm') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="userEditVisible"
      :title="t('settings.accDialogEdit')"
      width="480px"
      destroy-on-close
      align-center
      @closed="resetEditUserForm"
    >
      <el-form label-position="top">
        <el-form-item :label="t('settings.accFormUser')" required>
          <el-input v-model="userEditForm.username" clearable autocomplete="off" />
        </el-form-item>
        <el-form-item :label="t('settings.accFormPasswordEdit')">
          <el-input
            v-model="userEditForm.password"
            type="password"
            show-password
            :placeholder="t('settings.accFormPasswordPlaceholder')"
            autocomplete="new-password"
          />
        </el-form-item>
        <el-form-item :label="t('settings.accColStatus')">
          <el-select
            v-model="userEditForm.status"
            class="status-select"
            teleported
            placement="bottom-start"
            :fallback-placements="selectFallbackPlacementsBottom"
            :popper-options="selectPopperOptionsNoFlip"
          >
            <el-option :label="t('settings.accStatusActive')" value="active" />
            <el-option :label="t('settings.accStatusDisabled')" value="disabled" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('settings.accFormMenus')" required>
          <el-checkbox-group v-model="userEditForm.menu_keys" class="menu-check-group">
            <el-checkbox v-for="opt in menuOptions" :key="opt.key" :value="opt.key">
              {{ t(opt.labelKey) }}
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="userEditVisible = false">{{ t('settings.accCancel') }}</el-button>
        <el-button type="primary" :loading="userSaving" @click="submitEditUser">{{ t('settings.accConfirm') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { persistLocale, type AppLocale } from '../../../app/i18n'
import {
  SELECT_FALLBACK_PLACEMENTS_BOTTOM,
  selectPopperOptionsNoFlip,
} from '../../../shared/ui/elementSelectPlacement'
import {
  createPlatformUser,
  deletePlatformUser,
  fetchPlatformUsers,
  updatePlatformUser,
  type PlatformUserRow,
} from '../platformUsersApi'
import {
  getStoredUsername,
  isPlatformMenuAuth,
  syncPlatformMenusFromRemote,
  useAuthStore,
} from '../../auth/store/auth.store'

const { t, locale } = useI18n()
const selectFallbackPlacementsBottom = SELECT_FALLBACK_PLACEMENTS_BOTTOM
const auth = useAuthStore()

const menuOptions = [
  { key: 'insight', labelKey: 'menu.insight' },
  { key: 'smart-mining', labelKey: 'menu.smartMining' },
  { key: 'dictionary', labelKey: 'menu.dictionary' },
  { key: 'api-config', labelKey: 'menu.apiConfig' },
  { key: 'audit-log', labelKey: 'menu.auditLog' },
] as const

const usersLoading = ref(false)
const userSaving = ref(false)
const usersLoadError = ref('')
const userRows = ref<PlatformUserRow[]>([])
const userAddVisible = ref(false)
const userEditVisible = ref(false)
const editingUserId = ref<string | null>(null)
const editOpenedUsername = ref('')
const userAddForm = ref({
  username: '',
  password: '',
  menu_keys: [] as string[],
})
const userEditForm = ref({
  username: '',
  password: '',
  status: 'active' as 'active' | 'disabled',
  menu_keys: [] as string[],
})

function onSystemLangChange(v: string) {
  locale.value = v as AppLocale
  persistLocale(v as AppLocale)
}

function formatUserTime(iso: string) {
  try {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return iso
    return new Intl.DateTimeFormat(locale.value === 'zh-CN' ? 'zh-CN' : 'en-US', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }).format(d)
  } catch {
    return iso
  }
}

function usersFriendlyError(e: unknown): string {
  const raw = e instanceof Error ? e.message : String(e)
  try {
    const j = JSON.parse(raw) as { detail?: string | { code?: string } }
    const d = j?.detail
    if (typeof d === 'object' && d?.code === 'USERNAME_TAKEN') return t('settings.accUsernameTaken')
  } catch {
    /* ignore */
  }
  return raw || t('settings.accSaveFail')
}

async function loadUsers() {
  usersLoading.value = true
  usersLoadError.value = ''
  try {
    const res = await fetchPlatformUsers()
    userRows.value = res.items ?? []
  } catch (e) {
    userRows.value = []
    usersLoadError.value = usersFriendlyError(e) || t('settings.accLoadFail')
  } finally {
    usersLoading.value = false
  }
}

function openAddUser() {
  resetAddUserForm()
  userAddVisible.value = true
}

function resetAddUserForm() {
  userAddForm.value = { username: '', password: '', menu_keys: ['insight'] }
}

function resetEditUserForm() {
  editingUserId.value = null
  editOpenedUsername.value = ''
  userEditForm.value = { username: '', password: '', status: 'active', menu_keys: [] }
}

function openEditUser(row: PlatformUserRow) {
  editingUserId.value = row.id
  editOpenedUsername.value = row.username.trim()
  userEditForm.value = {
    username: row.username,
    password: '',
    status: row.status === 'disabled' ? 'disabled' : 'active',
    menu_keys: [...(row.menu_keys ?? [])],
  }
  userEditVisible.value = true
}

async function submitAddUser() {
  const u = userAddForm.value.username.trim()
  if (!u) {
    ElMessage.warning(t('settings.formRequired'))
    return
  }
  if (!userAddForm.value.password) {
    ElMessage.warning(t('settings.accNeedPassword'))
    return
  }
  if (!userAddForm.value.menu_keys.length) {
    ElMessage.warning(t('settings.accNeedMenus'))
    return
  }
  userSaving.value = true
  try {
    await createPlatformUser({
      username: u,
      password: userAddForm.value.password,
      menu_keys: [...userAddForm.value.menu_keys],
      status: 'active',
    })
    ElMessage.success(t('settings.accSaveOk'))
    userAddVisible.value = false
    await loadUsers()
  } catch (e) {
    ElMessage.error(usersFriendlyError(e))
  } finally {
    userSaving.value = false
  }
}

async function submitEditUser() {
  const id = editingUserId.value
  if (!id) return
  const u = userEditForm.value.username.trim()
  if (!u) {
    ElMessage.warning(t('settings.formRequired'))
    return
  }
  if (!userEditForm.value.menu_keys.length) {
    ElMessage.warning(t('settings.accNeedMenus'))
    return
  }
  userSaving.value = true
  try {
    const body: {
      username: string
      menu_keys: string[]
      status: 'active' | 'disabled'
      password?: string
    } = {
      username: u,
      menu_keys: [...userEditForm.value.menu_keys],
      status: userEditForm.value.status,
    }
    const pw = userEditForm.value.password.trim()
    if (pw) body.password = pw
    const updated = await updatePlatformUser(id, body)
    if (isPlatformMenuAuth() && editOpenedUsername.value === getStoredUsername()) {
      syncPlatformMenusFromRemote(updated.menu_keys ?? [], updated.username)
    }
    ElMessage.success(t('settings.accSaveOk'))
    userEditVisible.value = false
    await loadUsers()
  } catch (e) {
    ElMessage.error(usersFriendlyError(e))
  } finally {
    userSaving.value = false
  }
}

async function confirmDeleteUser(row: PlatformUserRow) {
  if (isCurrentLoginUser(row)) {
    ElMessage.warning(t('settings.accDeleteSelf'))
    return
  }
  try {
    await ElMessageBox.confirm(
      t('settings.accDeleteConfirm', { name: row.username }),
      locale.value === 'zh-CN' ? '提示' : 'Confirm',
      { type: 'warning' },
    )
  } catch {
    return
  }
  try {
    await deletePlatformUser(row.id)
    ElMessage.success(t('settings.accDeleteOk'))
    await loadUsers()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : t('settings.accDeleteFail'))
  }
}

onMounted(() => {
  void loadUsers()
})

function isCurrentLoginUser(row: PlatformUserRow): boolean {
  const rowName = (row.username || '').trim().toLowerCase()
  const currentName = resolveCurrentLoginUsername().toLowerCase()
  return !!rowName && !!currentName && rowName === currentName
}

function resolveCurrentLoginUsername(): string {
  const direct = (auth.displayUsername.value || getStoredUsername()).trim()
  if (direct) return direct
  try {
    const raw = localStorage.getItem('rsa_login_credentials')
    if (!raw) return ''
    const parsed = JSON.parse(raw) as { username?: string }
    return (parsed.username || '').trim()
  } catch {
    return ''
  }
}
</script>

<style scoped>
.config-block {
  margin-bottom: 28px;
  padding: 18px 20px 20px;
  background: #fff;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.config-block--intro {
  padding: 16px 20px;
}

.intro-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 10px;
}

.page-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  line-height: 1.35;
}

.intro-text {
  margin: 0;
  font-size: 15px;
  line-height: 1.55;
  color: var(--el-text-color-regular);
}

.block-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.block-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.block-subtitle {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.block-table {
  width: 100%;
}

.system-select {
  width: 148px;
  flex-shrink: 0;
}

.alert-below-header {
  margin-bottom: 12px;
}

.menu-check-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-start;
}

.status-select {
  width: 100%;
}

.row-action-btn:disabled {
  opacity: 0.45;
}
</style>
