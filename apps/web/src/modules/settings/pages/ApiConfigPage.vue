<template>
  <div>
    <section class="config-block config-block--intro">
      <h2 class="page-title">{{ t('settings.apiTitle') }}</h2>
      <p class="intro-text">{{ t('settings.apiPageIntro') }}</p>
    </section>

    <section class="config-block config-block--lang">
      <div class="system-row">
        <h3 class="block-title">{{ t('settings.moduleSystemLang') }}</h3>
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
      <div class="system-row">
        <h3 class="block-title">{{ t('settings.moduleSmartAgent') }}</h3>
        <el-select
          v-model="selectedAgentId"
          class="system-select"
          teleported
          placement="bottom-start"
          :fallback-placements="selectFallbackPlacementsBottom"
          :popper-options="selectPopperOptionsNoFlip"
          :placeholder="t('settings.selectSmartAgent')"
          @change="onAgentChange"
        >
          <el-option :label="t('settings.notSelected')" value="" />
          <el-option v-for="opt in agentSelectOptions" :key="opt.id" :label="opt.label" :value="opt.id" />
        </el-select>
      </div>
      <div class="system-row">
      </div>
    </section>

    <section class="config-block">
      <div class="block-head">
        <h3 class="block-title">{{ t('settings.moduleSmartAgent') }}</h3>
        <el-button type="primary" @click="openAddDialog('agent')">{{ t('settings.apiAdd') }}</el-button>
      </div>
      <el-table :data="agentRows" stripe class="block-table" :empty-text="t('settings.tableEmpty')">
        <el-table-column :label="t('settings.apiColName')" min-width="160" prop="name" />
        <el-table-column prop="model" :label="t('settings.apiColModel')" min-width="140" show-overflow-tooltip />
        <el-table-column prop="createdAt" :label="t('settings.colCreatedAt')" width="190" />
        <el-table-column :label="t('settings.colActions')" width="140" fixed="right">
          <template #default="{ row, $index }">
            <el-button type="primary" link @click="openEditDialog('agent', row, $index)">
              {{ t('settings.edit') }}
            </el-button>
            <el-button type="danger" link @click="onDelete('agent', $index)">
              {{ t('settings.delete') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
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
        <el-table-column :label="t('settings.accColStatus')" width="110">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
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
      v-model="dialogVisible"
      :title="dialogEditIndex === null ? t('settings.dialogAddTitle') : t('settings.dialogEditTitle')"
      width="520px"
      destroy-on-close
      @closed="resetForm"
    >
      <el-form label-position="top" class="dialog-form">
        <el-form-item :label="t('settings.formName')" required>
          <el-input v-model="form.name" clearable />
        </el-form-item>
        <el-form-item :label="t('settings.formBaseUrl')" required>
          <el-input v-model="form.baseUrl" clearable placeholder="https://api.example.com" />
        </el-form-item>
        <el-form-item :label="t('settings.formApiKey')">
          <el-input v-model="form.apiKey" type="password" show-password clearable autocomplete="off" />
        </el-form-item>
        <el-form-item :label="t('settings.formModel')">
          <el-input v-model="form.model" clearable />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ t('settings.dialogCancel') }}</el-button>
        <el-button type="primary" @click="submitDialog">{{ t('settings.dialogSave') }}</el-button>
      </template>
    </el-dialog>

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
import { computed, reactive, ref, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { persistLocale, type AppLocale } from '../../../app/i18n'
import type { ApiConfigRow } from '../apiConfig.shared'
import {
  agentApiConfigRows as agentRows,
} from '../apiConfig.shared'
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

type ModuleKey = 'agent'

const { t, locale } = useI18n()
const selectFallbackPlacementsBottom = SELECT_FALLBACK_PLACEMENTS_BOTTOM
const auth = useAuthStore()
const AGENT_SELECTED_KEY = 'rsa_settings_selected_agent_id'

function initialTopSelectId(storageKey: string, defaultId: string): string {
  try {
    const raw = localStorage.getItem(storageKey)
    if (raw === null) {
      localStorage.setItem(storageKey, defaultId)
      return defaultId
    }
    return raw
  } catch {
    return defaultId
  }
}

const dialogVisible = ref(false)
const dialogModule = ref<ModuleKey>('agent')
const dialogEditIndex = ref<number | null>(null)
const selectedAgentId = ref(initialTopSelectId(AGENT_SELECTED_KEY, ''))

const form = reactive({
  name: '',
  baseUrl: '',
  apiKey: '',
  model: '',
})

const menuOptions = [
  { key: 'insight', labelKey: 'menu.insight' },
  { key: 'pain-audit', labelKey: 'menu.painAudit' },
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

function nowStr() {
  const d = new Date()
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}

function newId() {
  return `cfg_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

function rowList(key: ModuleKey) {
  return agentRows
}

const agentSelectOptions = computed(() =>
  agentRows.value.map((row) => ({
    id: row.id,
    label: row.model ? `${row.name} · ${row.model}` : row.name,
  })),
)

function onAgentChange(v: string) {
  localStorage.setItem(AGENT_SELECTED_KEY, v || '')
}

watch(
  agentRows,
  () => {
    const sel = selectedAgentId.value
    if (sel && !agentRows.value.some((x) => x.id === sel)) {
      selectedAgentId.value = ''
      localStorage.setItem(AGENT_SELECTED_KEY, '')
    }
  },
  { deep: true },
)

function openAddDialog(key: ModuleKey) {
  dialogModule.value = key
  dialogEditIndex.value = null
  form.name = ''
  form.baseUrl = ''
  form.apiKey = ''
  form.model = ''
  dialogVisible.value = true
}

function openEditDialog(key: ModuleKey, row: ApiConfigRow, index: number) {
  dialogModule.value = key
  dialogEditIndex.value = index
  form.name = row.name
  form.baseUrl = row.baseUrl
  form.apiKey = row.apiKey
  form.model = row.model
  dialogVisible.value = true
}

function resetForm() {
  dialogEditIndex.value = null
}

function submitDialog() {
  const n = form.name.trim()
  const u = form.baseUrl.trim()
  if (!n || !u) {
    ElMessage.warning(t('settings.formRequired'))
    return
  }
  const list = rowList(dialogModule.value)
  if (dialogEditIndex.value === null) {
    list.value.push({
      id: newId(),
      name: n,
      baseUrl: u,
      apiKey: form.apiKey.trim(),
      model: form.model.trim(),
      createdAt: nowStr(),
    })
    ElMessage.success(t('settings.addSuccess'))
  } else {
    const i = dialogEditIndex.value
    const row = list.value[i]
    if (row) {
      row.name = n
      row.baseUrl = u
      row.apiKey = form.apiKey.trim()
      row.model = form.model.trim()
    }
    ElMessage.success(t('settings.dialogSave'))
  }
  dialogVisible.value = false
}

function rowDisplayName(key: ModuleKey, row: ApiConfigRow): string {
  return row.name
}

async function onDelete(key: ModuleKey, index: number) {
  const list = rowList(key)
  const row = list.value[index]
  if (!row) return
  try {
    await ElMessageBox.confirm(
      t('settings.deleteConfirm', { name: rowDisplayName(key, row) }),
      t('layout.logoutTitle'),
      { type: 'warning' },
    )
    list.value.splice(index, 1)
    ElMessage.success(t('settings.deleteSuccess'))
  } catch {
    /* cancel */
  }
}

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
  if (row.username === auth.displayUsername.value) {
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

.page-title {
  margin: 0 0 10px;
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

.config-block--lang {
  padding-bottom: 18px;
}

.block-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.block-head-add {
  flex-shrink: 0;
  margin-top: 2px;
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

.system-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.system-row + .system-row {
  margin-top: 14px;
}

.system-select {
  width: 148px;
  flex-shrink: 0;
}

.dialog-form {
  padding-top: 4px;
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
