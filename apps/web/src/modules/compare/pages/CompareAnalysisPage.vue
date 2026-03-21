<template>
  <el-card class="view-card">
    <header class="page-header">
      <h2 class="page-title">{{ t('compare.title') }}</h2>
      <p class="page-subtitle">{{ t('compare.pageSubtitle') }}</p>
    </header>
    <div class="toolbar">
      <el-button type="primary" @click="onAddCompare">{{ t('compare.addCompare') }}</el-button>
      <el-button :icon="Refresh" @click="onRefresh" :title="t('compare.refresh')" />
    </div>

    <el-table :data="pagedRows" stripe class="compare-table" :empty-text="t('compare.tableEmpty')">
      <el-table-column :label="t('compare.colIndex')" width="64" align="center">
        <template #default="{ $index }">
          {{ (page - 1) * pageSize + $index + 1 }}
        </template>
      </el-table-column>
      <el-table-column prop="asin1" :label="t('compare.colAsin1')" min-width="132" show-overflow-tooltip />
      <el-table-column prop="asin2" :label="t('compare.colAsin2')" min-width="132" show-overflow-tooltip />
      <el-table-column prop="creator" :label="t('compare.colCreator')" width="120" show-overflow-tooltip />
      <el-table-column prop="createdAt" :label="t('compare.colCreatedAt')" width="168" />
      <el-table-column prop="smartModel" :label="t('compare.colSmartModel')" width="128" show-overflow-tooltip />
      <el-table-column :label="t('compare.colStatus')" width="112">
        <template #default="{ row }">
          <span class="status-text">{{ row.statusLabel }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="t('compare.colActions')" min-width="140" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="onViewResults(row)">{{ t('compare.viewResults') }}</el-button>
          <el-button
            type="danger"
            link
            :disabled="row.id.startsWith('demo')"
            @click="onDeleteCompare(row)"
          >
            {{ t('compare.delete') }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pager-bar">
      <div class="pager-left">
        <span class="pager-total">{{ t('compare.pagerTotal', { n: rows.length }) }}</span>
        <span class="pager-per">
          <span class="pager-per-label">{{ t('compare.pagerPerPage') }}</span>
          <el-select
            v-model="pageSize"
            class="pager-size-select"
            :teleported="false"
            @change="onPageSizeChange"
          >
            <el-option v-for="s in pageSizeOptions" :key="s" :label="String(s)" :value="s" />
          </el-select>
          <span class="pager-per-suffix">{{ t('compare.pagerItemsUnit') }}</span>
        </span>
      </div>
      <el-pagination
        v-model:current-page="page"
        class="pager-nav"
        :page-size="pageSize"
        :total="rows.length"
        layout="prev, pager, next"
        :pager-count="7"
        background
        :hide-on-single-page="false"
      />
    </div>

    <el-dialog
      v-model="addDialogVisible"
      :title="t('compare.dialogAddCompare')"
      width="560px"
      destroy-on-close
      @closed="resetAddForm"
    >
      <el-form label-position="top" class="add-dialog-form">
        <p class="dialog-hint">{{ t('compare.dialogInsightOnlyHint') }}</p>
        <el-form-item :label="t('compare.formAsin1')" required>
          <el-select
            v-model="asin1Key"
            filterable
            clearable
            :loading="insightTasksLoading"
            :teleported="false"
            :placeholder="t('compare.formAsinPh')"
            class="asin-select"
          >
            <el-option
              v-for="opt in insightProductOptions"
              :key="opt.key"
              :label="opt.label"
              :value="opt.key"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('compare.formAsin2')" required>
          <el-select
            v-model="asin2Key"
            filterable
            clearable
            :loading="insightTasksLoading"
            :teleported="false"
            :placeholder="t('compare.formAsinPh')"
            class="asin-select"
          >
            <el-option
              v-for="opt in insightProductOptions"
              :key="opt.key"
              :label="opt.label"
              :value="opt.key"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialogVisible = false">{{ t('compare.dialogCancel') }}</el-button>
        <el-button type="primary" :loading="dialogSubmitting" @click="submitAddCompare">
          {{ t('compare.dialogConfirm') }}
        </el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { insightApiConfigRows } from '../../settings/apiConfig.shared'
import { formatInsightModelLineByProviderId } from '../../../shared/utils/insightModelLabel'
import { fetchInsightTasks } from '../../tasks/api'
import type { InsightTaskRow } from '../../tasks/types'
import { getStoredUsername } from '../../auth/store/auth.store'
import { ComparePrerequisiteError, fetchCompareProducts } from '../api'
import {
  deleteCompareRun,
  loadCompareRuns,
  upsertCompareRun,
  type StoredCompareRun,
} from '../compareRuns.storage'

/** 列表「模型」列固定展示（与结果页分析源一致口径） */
const COMPARE_LIST_MODEL_LABEL = 'rsa-v1'

const { t, locale } = useI18n()
const router = useRouter()

type CompareTableRow = {
  id: string
  asin1: string
  asin2: string
  creator: string
  createdAt: string
  smartModel: string
  status: 'success' | 'failed'
  statusLabel: string
  platformA: string
  platformB: string
}

type InsightProductOption = {
  key: string
  platform: string
  product_id: string
  analysis_provider_id: string | null
  label: string
}

const page = ref(1)
const pageSize = ref(20)
const pageSizeOptions = [10, 20, 50] as const

const addDialogVisible = ref(false)
const asin1Key = ref('')
const asin2Key = ref('')
const insightProductOptions = ref<InsightProductOption[]>([])
const insightTasksLoading = ref(false)
const dialogSubmitting = ref(false)

const rows = ref<CompareTableRow[]>([])

function formatTaskTime(iso: string) {
  if (!iso) return '—'
  return iso.slice(0, 19).replace('T', ' ')
}

function currentCreatorLabel(): string {
  const u = getStoredUsername()
  if (u) return u
  const zh = locale.value === 'zh-CN'
  const role = localStorage.getItem('rsa_user_role') || 'readonly'
  if (zh) {
    if (role === 'admin') return '超级管理员'
    if (role === 'operator') return '分析师'
    return '只读'
  }
  if (role === 'admin') return 'Admin'
  if (role === 'operator') return 'Operator'
  return 'Read-only'
}

function statusLabelFor(status: 'success' | 'failed') {
  return status === 'success' ? t('compare.taskStatus.success') : t('compare.taskStatus.failed')
}

function mapStoredToRow(s: StoredCompareRun): CompareTableRow {
  return {
    id: s.id,
    asin1: s.product_id_a,
    asin2: s.product_id_b,
    creator: s.creator,
    createdAt: formatTaskTime(s.created_at_iso),
    smartModel: COMPARE_LIST_MODEL_LABEL,
    status: s.status,
    statusLabel: statusLabelFor(s.status),
    platformA: s.platform_a,
    platformB: s.platform_b,
  }
}

function buildDefaultRows(): CompareTableRow[] {
  const zh = locale.value === 'zh-CN'
  return [
    {
      id: 'demo-1',
      asin1: 'B0XXXXTEST1',
      asin2: 'B0XXXXTEST2',
      creator: zh ? '超级管理员' : 'Super admin',
      createdAt: '2026-03-18 14:22',
      smartModel: COMPARE_LIST_MODEL_LABEL,
      status: 'success',
      statusLabel: statusLabelFor('success'),
      platformA: 'amazon',
      platformB: 'amazon',
    },
    {
      id: 'demo-2',
      asin1: 'B0XXXXTEST3',
      asin2: 'B0XXXXTEST4',
      creator: zh ? '分析师' : 'Analyst',
      createdAt: '2026-03-17 09:05',
      smartModel: COMPARE_LIST_MODEL_LABEL,
      status: 'success',
      statusLabel: statusLabelFor('success'),
      platformA: 'amazon',
      platformB: 'amazon',
    },
    {
      id: 'demo-3',
      asin1: 'B0XXXXTEST5',
      asin2: 'B0XXXXTEST6',
      creator: zh ? '超级管理员' : 'Super admin',
      createdAt: '2026-03-16 18:40',
      smartModel: COMPARE_LIST_MODEL_LABEL,
      status: 'failed',
      statusLabel: statusLabelFor('failed'),
      platformA: 'amazon',
      platformB: 'amazon',
    },
  ]
}

function loadRows() {
  const stored = loadCompareRuns()
  if (stored.length === 0) {
    rows.value = buildDefaultRows()
  } else {
    rows.value = stored.map(mapStoredToRow)
  }
}

onMounted(() => {
  loadRows()
})

watch(locale, () => {
  loadRows()
})

function onPageSizeChange() {
  page.value = 1
}

const pagedRows = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return rows.value.slice(start, start + pageSize.value)
})

function resetAddForm() {
  asin1Key.value = ''
  asin2Key.value = ''
}

function displayProviderLabel(providerId: string | null) {
  return formatInsightModelLineByProviderId(providerId, insightApiConfigRows.value, t)
}

function optionByKey(key: string): InsightProductOption | undefined {
  return insightProductOptions.value.find((o) => o.key === key)
}

async function loadInsightProductsForDialog() {
  insightTasksLoading.value = true
  try {
    const res = await fetchInsightTasks({ status: 'success', limit: 200 })
    const best = new Map<string, InsightTaskRow>()
    for (const task of res.items ?? []) {
      const pair = `${task.platform}|${task.product_id}`
      const prev = best.get(pair)
      if (!prev || task.created_at > prev.created_at) best.set(pair, task)
    }
    insightProductOptions.value = [...best.values()]
      .map((task) => ({
        key: `${task.platform}|${task.product_id}`,
        platform: task.platform,
        product_id: task.product_id,
        analysis_provider_id: task.analysis_provider_id,
        label: `${task.product_id} · ${task.platform}`,
      }))
      .sort((a, b) => a.product_id.localeCompare(b.product_id))
  } catch {
    ElMessage.warning(t('compare.insightProductsLoadFailed'))
    insightProductOptions.value = []
  } finally {
    insightTasksLoading.value = false
  }
}

watch(addDialogVisible, (open) => {
  if (open) void loadInsightProductsForDialog()
})

function onAddCompare() {
  addDialogVisible.value = true
}

function onRefresh() {
  loadRows()
  ElMessage.success(t('compare.refreshed'))
}

type CompareRunPayload = {
  platform_a: string
  product_id_a: string
  platform_b: string
  product_id_b: string
  model_id: string
  model_label: string
}

async function runCompareAndPersist(payload: CompareRunPayload): Promise<boolean> {
  const { platform_a: pa, product_id_a: ida, platform_b: pb, product_id_b: idb, model_id: mid, model_label: modelLabel } =
    payload

  const runId = crypto.randomUUID()
  const createdIso = new Date().toISOString()

  try {
    const result = await fetchCompareProducts({
      platform_a: pa,
      product_id_a: ida,
      platform_b: pb,
      product_id_b: idb,
    })
    upsertCompareRun({
      id: runId,
      platform_a: pa,
      product_id_a: ida,
      platform_b: pb,
      product_id_b: idb,
      creator: currentCreatorLabel(),
      created_at_iso: createdIso,
      model_id: mid || undefined,
      model_label: modelLabel,
      status: 'success',
      result,
    })
    return true
  } catch (e) {
    let errMsg = t('compare.compareFailed')
    if (e instanceof ComparePrerequisiteError) {
      const d = e.detail
      errMsg = locale.value === 'zh-CN' ? d.messages.zh_CN : d.messages.en
    } else if (e instanceof Error) {
      errMsg = e.message
    }
    upsertCompareRun({
      id: runId,
      platform_a: pa,
      product_id_a: ida,
      platform_b: pb,
      product_id_b: idb,
      creator: currentCreatorLabel(),
      created_at_iso: createdIso,
      model_id: mid || undefined,
      model_label: modelLabel,
      status: 'failed',
      error_message: errMsg,
    })
    ElMessage.warning(errMsg)
    return false
  }
}

async function submitAddCompare() {
  const k1 = asin1Key.value
  const k2 = asin2Key.value
  if (!k1 || !k2) {
    ElMessage.warning(t('compare.needPickAsins'))
    return
  }
  if (k1 === k2) {
    ElMessage.warning(t('compare.sameProductBothSides'))
    return
  }
  const oa = optionByKey(k1)
  const ob = optionByKey(k2)
  if (!oa || !ob) {
    ElMessage.warning(t('compare.insightPickStale'))
    void loadInsightProductsForDialog()
    return
  }

  const mid = oa.analysis_provider_id ?? ''
  const modelLabel = displayProviderLabel(oa.analysis_provider_id)

  const payload: CompareRunPayload = {
    platform_a: oa.platform,
    product_id_a: oa.product_id,
    platform_b: ob.platform,
    product_id_b: ob.product_id,
    model_id: mid,
    model_label: modelLabel,
  }

  dialogSubmitting.value = true
  try {
    const ok = await runCompareAndPersist(payload)
    loadRows()
    if (ok) {
      addDialogVisible.value = false
      resetAddForm()
      page.value = 1
      ElMessage.success(t('compare.compareSaved'))
    }
  } finally {
    dialogSubmitting.value = false
  }
}

function onViewResults(row: CompareTableRow) {
  void router.push({
    path: `/compare-analysis/result/${encodeURIComponent(row.id)}`,
  })
}

async function onDeleteCompare(row: CompareTableRow) {
  if (row.id.startsWith('demo')) {
    ElMessage.info(t('compare.deleteDemo'))
    return
  }
  try {
    await ElMessageBox.confirm(t('compare.deleteConfirm'), t('layout.logoutTitle'), {
      type: 'warning',
    })
  } catch {
    return
  }
  deleteCompareRun(row.id)
  loadRows()
  ElMessage.success(t('compare.deleteOk'))
  if (pagedRows.value.length === 0 && page.value > 1) {
    page.value = Math.max(1, page.value - 1)
  }
}
</script>

<style scoped>
.view-card {
  border-radius: 10px;
  border: 1px solid #ebeef2;
  box-shadow: none;
}

.page-header {
  margin-bottom: 18px;
}

.page-title {
  margin: 0 0 8px;
  font-size: 20px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  line-height: 1.3;
}

.page-subtitle {
  margin: 0;
  font-size: 14px;
  line-height: 1.55;
  color: var(--el-text-color-secondary);
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.compare-table {
  width: 100%;
}

.status-text {
  font-size: 13px;
  color: var(--el-text-color-regular);
}

.pager-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  width: 100%;
  margin-top: 4px;
  padding-top: 16px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.pager-left {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}

.pager-total {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  line-height: 32px;
}

.pager-per {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.pager-size-select {
  width: 72px;
}

.pager-size-select :deep(.el-select__wrapper) {
  min-height: 32px;
  padding: 4px 10px;
  border-radius: 6px;
}

.pager-nav {
  flex-shrink: 0;
}

.pager-nav:deep(.btn-prev),
.pager-nav:deep(.btn-next),
.pager-nav:deep(.el-pager li) {
  border-radius: 6px;
  min-width: 32px;
  font-weight: 500;
}

.add-dialog-form {
  padding-top: 4px;
}

.dialog-hint {
  margin: 0 0 14px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--el-text-color-secondary);
}

.asin-select {
  width: 100%;
}
</style>
