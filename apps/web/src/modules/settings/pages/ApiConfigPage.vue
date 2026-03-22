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
        <h3 class="block-title">{{ t('settings.translateShort') }}</h3>
        <el-select
          v-model="selectedTranslateApiId"
          class="system-select"
          teleported
          placement="bottom-start"
          :fallback-placements="selectFallbackPlacementsBottom"
          :popper-options="selectPopperOptionsNoFlip"
          :placeholder="t('settings.selectTranslateApi')"
          @change="onTranslateApiChange"
        >
          <el-option :label="t('settings.notSelected')" value="" />
          <el-option v-for="opt in translateSelectOptions" :key="opt.id" :label="opt.label" :value="opt.id" />
        </el-select>
      </div>
      <div class="system-row">
        <h3 class="block-title">{{ t('settings.reviewFetchShort') }}</h3>
        <el-select
          v-model="selectedReviewFetchApiId"
          class="system-select"
          teleported
          placement="bottom-start"
          :fallback-placements="selectFallbackPlacementsBottom"
          :popper-options="selectPopperOptionsNoFlip"
          :placeholder="t('settings.selectReviewFetchApi')"
          @change="onReviewFetchApiChange"
        >
          <el-option :label="t('settings.notSelected')" value="" />
          <el-option v-for="opt in reviewFetchSelectOptions" :key="opt.id" :label="opt.label" :value="opt.id" />
        </el-select>
      </div>
    </section>

    <section class="config-block">
      <div class="block-head">
        <h3 class="block-title">{{ t('settings.moduleInsightModel') }}</h3>
        <el-button type="primary" @click="openAddDialog('insight')">{{ t('settings.apiAdd') }}</el-button>
      </div>
      <el-table :data="insightRows" stripe class="block-table" :empty-text="t('settings.tableEmpty')">
        <el-table-column :label="t('settings.apiColName')" min-width="160">
          <template #default="{ row }">
            {{ insightTableName(row) }}
          </template>
        </el-table-column>
        <el-table-column prop="model" :label="t('settings.apiColModel')" min-width="140" show-overflow-tooltip />
        <el-table-column prop="createdAt" :label="t('settings.colCreatedAt')" width="190" />
        <el-table-column :label="t('settings.colActions')" width="140" fixed="right">
          <template #default="{ row, $index }">
            <el-button
              type="primary"
              link
              class="row-action-btn"
              :disabled="row.builtin"
              @click="openEditDialog('insight', row, $index)"
            >
              {{ t('settings.edit') }}
            </el-button>
            <el-button
              type="danger"
              link
              class="row-action-btn"
              :disabled="row.builtin"
              @click="onDelete('insight', $index)"
            >
              {{ t('settings.delete') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
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

    <section class="config-block">
      <div class="block-head">
        <div>
          <h3 class="block-title">{{ t('settings.moduleReviewFetchApi') }}</h3>
        </div>
        <el-button type="primary" class="block-head-add" @click="openAddDialog('reviewFetch')">
          {{ t('settings.apiAdd') }}
        </el-button>
      </div>
      <el-table :data="reviewFetchRows" stripe class="block-table" :empty-text="t('settings.tableEmpty')">
        <el-table-column :label="t('settings.apiColName')" min-width="160">
          <template #default="{ row }">
            {{ row.builtin ? t('settings.defaultConfigLabel') : row.name }}
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" :label="t('settings.colCreatedAt')" width="190" />
        <el-table-column :label="t('settings.colActions')" width="140" fixed="right">
          <template #default="{ row, $index }">
            <el-button
              type="primary"
              link
              class="row-action-btn"
              :disabled="row.builtin"
              @click="openEditDialog('reviewFetch', row, $index)"
            >
              {{ t('settings.edit') }}
            </el-button>
            <el-button
              type="danger"
              link
              class="row-action-btn"
              :disabled="row.builtin"
              @click="onDelete('reviewFetch', $index)"
            >
              {{ t('settings.delete') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <section class="config-block">
      <div class="block-head">
        <h3 class="block-title">{{ t('settings.moduleTranslateApi') }}</h3>
        <el-button type="primary" @click="openAddDialog('translate')">{{ t('settings.apiAdd') }}</el-button>
      </div>
      <el-table :data="translateRows" stripe class="block-table" :empty-text="t('settings.tableEmpty')">
        <el-table-column :label="t('settings.apiColName')" min-width="160">
          <template #default="{ row }">
            {{ row.builtin ? t('settings.defaultConfigLabel') : row.name }}
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" :label="t('settings.colCreatedAt')" width="190" />
        <el-table-column :label="t('settings.colActions')" width="140" fixed="right">
          <template #default="{ row, $index }">
            <el-button
              type="primary"
              link
              class="row-action-btn"
              :disabled="row.builtin"
              @click="openEditDialog('translate', row, $index)"
            >
              {{ t('settings.edit') }}
            </el-button>
            <el-button
              type="danger"
              link
              class="row-action-btn"
              :disabled="row.builtin"
              @click="onDelete('translate', $index)"
            >
              {{ t('settings.delete') }}
            </el-button>
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
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { persistLocale, type AppLocale } from '../../../app/i18n'
import type { ApiConfigRow } from '../apiConfig.shared'
import {
  agentApiConfigRows as agentRows,
  insightApiConfigRows as insightRows,
  reviewFetchApiConfigRows as reviewFetchRows,
  translateApiConfigRows as translateRows,
} from '../apiConfig.shared'
import {
  SELECT_FALLBACK_PLACEMENTS_BOTTOM,
  selectPopperOptionsNoFlip,
} from '../../../shared/ui/elementSelectPlacement'

type ModuleKey = 'insight' | 'agent' | 'reviewFetch' | 'translate'

const { t, locale } = useI18n()
const selectFallbackPlacementsBottom = SELECT_FALLBACK_PLACEMENTS_BOTTOM
const TRANSLATE_SELECTED_KEY = 'rsa_settings_selected_translate_api_id'
const REVIEW_FETCH_SELECTED_KEY = 'rsa_settings_selected_review_fetch_api_id'
const DEFAULT_TRANSLATE_ID = 'tr_default'
const DEFAULT_REVIEW_FETCH_ID = 'rf_pangolin'

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
const dialogModule = ref<ModuleKey>('insight')
const dialogEditIndex = ref<number | null>(null)
const selectedTranslateApiId = ref(initialTopSelectId(TRANSLATE_SELECTED_KEY, DEFAULT_TRANSLATE_ID))
const selectedReviewFetchApiId = ref(initialTopSelectId(REVIEW_FETCH_SELECTED_KEY, DEFAULT_REVIEW_FETCH_ID))

const form = reactive({
  name: '',
  baseUrl: '',
  apiKey: '',
  model: '',
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
  if (key === 'insight') return insightRows
  if (key === 'agent') return agentRows
  if (key === 'reviewFetch') return reviewFetchRows
  return translateRows
}

function insightTableName(row: ApiConfigRow) {
  const n = row.name?.trim()
  if (row.builtin && n) return n
  if (row.builtin) return t('settings.insightBuiltinModelName')
  return row.name
}

const translateSelectOptions = computed(() =>
  translateRows.value.map((row) => ({
    id: row.id,
    label: row.builtin
      ? t('settings.defaultConfigLabel')
      : row.model
        ? `${row.name} · ${row.model}`
        : row.name,
  })),
)

const reviewFetchSelectOptions = computed(() =>
  reviewFetchRows.value.map((row) => ({
    id: row.id,
    label: row.builtin
      ? t('settings.defaultConfigLabel')
      : row.model
        ? `${row.name} · ${row.model}`
        : row.name,
  })),
)

function onTranslateApiChange(v: string) {
  localStorage.setItem(TRANSLATE_SELECTED_KEY, v || '')
}

function onReviewFetchApiChange(v: string) {
  localStorage.setItem(REVIEW_FETCH_SELECTED_KEY, v || '')
}

watch(
  translateRows,
  () => {
    const sel = selectedTranslateApiId.value
    if (sel && !translateRows.value.some((x) => x.id === sel)) {
      selectedTranslateApiId.value = DEFAULT_TRANSLATE_ID
      localStorage.setItem(TRANSLATE_SELECTED_KEY, DEFAULT_TRANSLATE_ID)
    }
  },
  { deep: true },
)

watch(
  reviewFetchRows,
  () => {
    const sel = selectedReviewFetchApiId.value
    if (sel && !reviewFetchRows.value.some((x) => x.id === sel)) {
      selectedReviewFetchApiId.value = DEFAULT_REVIEW_FETCH_ID
      localStorage.setItem(REVIEW_FETCH_SELECTED_KEY, DEFAULT_REVIEW_FETCH_ID)
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
  if (row.builtin && (key === 'insight' || key === 'reviewFetch' || key === 'translate')) return
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
    if (
      row?.builtin &&
      (dialogModule.value === 'insight' ||
        dialogModule.value === 'reviewFetch' ||
        dialogModule.value === 'translate')
    ) {
      ElMessage.warning(t('settings.builtinNotEditable'))
      return
    }
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
  if (row.builtin) {
    if (key === 'insight') return t('settings.insightBuiltinModelName')
    if (key === 'reviewFetch' || key === 'translate') return t('settings.defaultConfigLabel')
  }
  return row.name
}

async function onDelete(key: ModuleKey, index: number) {
  const list = rowList(key)
  const row = list.value[index]
  if (!row) return
  if (row.builtin && (key === 'insight' || key === 'reviewFetch' || key === 'translate')) return
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

.row-action-btn:disabled {
  opacity: 0.45;
}
</style>
