<template>
  <div class="page">
    <el-card class="panel" v-loading="loading">
      <template #header>
        <div class="panel-header">
          <div class="panel-header-text">
            <h3>{{ t('settings.accTitle') }}</h3>
            <p>{{ t('settings.accDesc') }}</p>
          </div>
          <el-button type="primary" class="acc-add-btn" @click="openAdd">
            {{ t('settings.accAdd') }}
          </el-button>
        </div>
      </template>
      <el-alert
        v-if="loadError"
        type="error"
        :title="loadError"
        :closable="false"
        class="alert-below-header"
      />
      <el-table :data="items" stripe>
        <el-table-column prop="username" :label="t('settings.accColUser')" min-width="140" />
        <el-table-column :label="t('settings.accColStatus')" width="110">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
              {{
                row.status === 'active'
                  ? t('settings.accStatusActive')
                  : t('settings.accStatusDisabled')
              }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('settings.accColCreated')" width="188">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column :label="t('settings.accColActions')" width="168" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="openEdit(row)">{{ t('settings.accEdit') }}</el-button>
            <el-button type="danger" link @click="confirmDelete(row)">{{ t('settings.accDelete') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="addVisible"
      :title="t('settings.accDialogAdd')"
      width="480px"
      destroy-on-close
      align-center
      @closed="resetAddForm"
    >
      <el-form label-position="top">
        <el-form-item :label="t('settings.accFormUser')" required>
          <el-input v-model="addForm.username" clearable autocomplete="off" />
        </el-form-item>
        <el-form-item :label="t('settings.accFormPassword')" required>
          <el-input
            v-model="addForm.password"
            type="password"
            show-password
            autocomplete="new-password"
          />
        </el-form-item>
        <el-form-item :label="t('settings.accFormMenus')" required>
          <el-checkbox-group v-model="addForm.menu_keys" class="menu-check-group">
            <el-checkbox v-for="opt in menuOptions" :key="opt.key" :value="opt.key">
              {{ t(opt.labelKey) }}
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addVisible = false">{{ t('settings.accCancel') }}</el-button>
        <el-button type="primary" :loading="saving" @click="submitAdd">{{ t('settings.accConfirm') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="editVisible"
      :title="t('settings.accDialogEdit')"
      width="480px"
      destroy-on-close
      align-center
      @closed="resetEditForm"
    >
      <el-form label-position="top">
        <el-form-item :label="t('settings.accFormUser')" required>
          <el-input v-model="editForm.username" clearable autocomplete="off" />
        </el-form-item>
        <el-form-item :label="t('settings.accFormPasswordEdit')">
          <el-input
            v-model="editForm.password"
            type="password"
            show-password
            :placeholder="t('settings.accFormPasswordPlaceholder')"
            autocomplete="new-password"
          />
        </el-form-item>
        <el-form-item :label="t('settings.accColStatus')">
          <el-select
            v-model="editForm.status"
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
          <el-checkbox-group v-model="editForm.menu_keys" class="menu-check-group">
            <el-checkbox v-for="opt in menuOptions" :key="opt.key" :value="opt.key">
              {{ t(opt.labelKey) }}
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">{{ t('settings.accCancel') }}</el-button>
        <el-button type="primary" :loading="saving" @click="submitEdit">{{ t('settings.accConfirm') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getStoredUsername,
  isPlatformMenuAuth,
  syncPlatformMenusFromRemote,
  useAuthStore,
} from '../../auth/store/auth.store'
import {
  createPlatformUser,
  deletePlatformUser,
  fetchPlatformUsers,
  updatePlatformUser,
  type PlatformUserRow,
} from '../platformUsersApi'
import {
  SELECT_FALLBACK_PLACEMENTS_BOTTOM,
  selectPopperOptionsNoFlip,
} from '../../../shared/ui/elementSelectPlacement'

const { t, locale } = useI18n()
const selectFallbackPlacementsBottom = SELECT_FALLBACK_PLACEMENTS_BOTTOM
const auth = useAuthStore()

const menuOptions = [
  { key: 'insight', labelKey: 'menu.insight' },
  { key: 'pain-audit', labelKey: 'menu.painAudit' },
  { key: 'dictionary', labelKey: 'menu.dictionary' },
  { key: 'api-config', labelKey: 'menu.apiConfig' },
  { key: 'audit-log', labelKey: 'menu.auditLog' },
  { key: 'account-permissions', labelKey: 'menu.accountPermissions' },
] as const

const loading = ref(false)
const saving = ref(false)
const loadError = ref('')
const items = ref<PlatformUserRow[]>([])

const addVisible = ref(false)
const addForm = ref({
  username: '',
  password: '',
  menu_keys: [] as string[],
})

const editVisible = ref(false)
const editingId = ref<string | null>(null)
/** 打开编辑弹窗时的用户名，用于判断是否在改「当前登录用户」的权限 */
const editOpenedUsername = ref('')
const editForm = ref({
  username: '',
  password: '',
  status: 'active' as 'active' | 'disabled',
  menu_keys: [] as string[],
})

function formatTime(iso: string) {
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

function friendlyError(e: unknown): string {
  const raw = e instanceof Error ? e.message : String(e)
  try {
    const j = JSON.parse(raw) as { detail?: string | { code?: string } }
    const d = j?.detail
    if (typeof d === 'object' && d?.code === 'USERNAME_TAKEN') return t('settings.accUsernameTaken')
  } catch {
    /* not json */
  }
  return raw || t('settings.accSaveFail')
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await fetchPlatformUsers()
    items.value = res.items ?? []
  } catch (e) {
    items.value = []
    loadError.value = friendlyError(e) || t('settings.accLoadFail')
  } finally {
    loading.value = false
  }
}

function openAdd() {
  resetAddForm()
  addVisible.value = true
}

function resetAddForm() {
  addForm.value = { username: '', password: '', menu_keys: ['insight'] }
}

function resetEditForm() {
  editingId.value = null
  editOpenedUsername.value = ''
  editForm.value = { username: '', password: '', status: 'active', menu_keys: [] }
}

function openEdit(row: PlatformUserRow) {
  editingId.value = row.id
  editOpenedUsername.value = row.username.trim()
  editForm.value = {
    username: row.username,
    password: '',
    status: row.status === 'disabled' ? 'disabled' : 'active',
    menu_keys: [...(row.menu_keys ?? [])],
  }
  editVisible.value = true
}

async function submitAdd() {
  const u = addForm.value.username.trim()
  if (!u) {
    ElMessage.warning(t('settings.formRequired'))
    return
  }
  if (!addForm.value.password) {
    ElMessage.warning(t('settings.accNeedPassword'))
    return
  }
  if (!addForm.value.menu_keys.length) {
    ElMessage.warning(t('settings.accNeedMenus'))
    return
  }
  saving.value = true
  try {
    await createPlatformUser({
      username: u,
      password: addForm.value.password,
      menu_keys: [...addForm.value.menu_keys],
      status: 'active',
    })
    ElMessage.success(t('settings.accSaveOk'))
    addVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(friendlyError(e))
  } finally {
    saving.value = false
  }
}

async function submitEdit() {
  const id = editingId.value
  if (!id) return
  const u = editForm.value.username.trim()
  if (!u) {
    ElMessage.warning(t('settings.formRequired'))
    return
  }
  if (!editForm.value.menu_keys.length) {
    ElMessage.warning(t('settings.accNeedMenus'))
    return
  }
  saving.value = true
  try {
    const body: {
      username: string
      menu_keys: string[]
      status: 'active' | 'disabled'
      password?: string
    } = {
      username: u,
      menu_keys: [...editForm.value.menu_keys],
      status: editForm.value.status,
    }
    const pw = editForm.value.password.trim()
    if (pw) body.password = pw
    const updated = await updatePlatformUser(id, body)
    if (isPlatformMenuAuth() && editOpenedUsername.value === getStoredUsername()) {
      syncPlatformMenusFromRemote(updated.menu_keys ?? [], updated.username)
    }
    ElMessage.success(t('settings.accSaveOk'))
    editVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(friendlyError(e))
  } finally {
    saving.value = false
  }
}

async function confirmDelete(row: PlatformUserRow) {
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
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : t('settings.accDeleteFail'))
  }
}

onMounted(() => {
  void load()
})
</script>

<style scoped>
.page {
  height: 100%;
}
.panel {
  border-radius: 10px;
  border: 1px solid #ebeef2;
  box-shadow: none;
}
.panel :deep(.el-card__header) {
  padding: 14px 18px;
  border-bottom: 1px solid #f2f4f7;
}
.panel :deep(.el-card__body) {
  padding: 12px 18px 16px;
}
.panel-header {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0;
}
.panel-header-text h3 {
  margin: 0;
  color: #111827;
  font-size: 18px;
}
.panel-header-text p {
  margin: 6px 0 0;
  color: #6b7280;
  font-size: 14px;
}
.acc-add-btn {
  margin-top: 12px;
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
</style>
