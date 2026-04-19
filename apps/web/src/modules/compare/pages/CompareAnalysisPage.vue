<template>
  <el-card class="view-card" v-loading="listLoading">
    <header class="page-header">
      <h2 class="page-title">{{ t('compare.title') }}</h2>
      <p class="page-subtitle">{{ t('compare.pageSubtitle') }}</p>
    </header>
    <div class="toolbar">
      <el-button type="primary" :disabled="!canMutateCompare" @click="onAddCompare">
        {{ t('compare.addCompare') }}
      </el-button>
      <el-button
        class="toolbar-refresh-square"
        :icon="Refresh"
        :loading="listLoading"
        @click="onRefresh"
        :title="t('compare.refresh')"
      />
    </div>

    <el-table :data="pagedRows" stripe class="compare-table" :empty-text="t('compare.tableEmpty')">
      <el-table-column prop="asin1" :label="t('compare.colAsin1')" min-width="132" show-overflow-tooltip />
      <el-table-column prop="asin2" :label="t('compare.colAsin2')" min-width="132" show-overflow-tooltip />
      <el-table-column
        prop="analysisModel"
        :label="t('compare.colAnalysisModel')"
        min-width="140"
        show-overflow-tooltip
      />
      <el-table-column :label="t('compare.colAnalysisStatus')" width="112">
        <template #default="{ row }">
          <span class="status-text">{{ compareFlowStatusLabel(row.status) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="creator" :label="t('compare.colCreator')" width="120" show-overflow-tooltip />
      <el-table-column prop="createdAt" :label="t('compare.colCreatedAt')" width="168" />
      <el-table-column :label="t('compare.colActions')" min-width="200" fixed="right" align="center">
        <template #default="{ row }">
          <div class="compare-actions">
            <el-button type="primary" size="small" @click="onViewResults(row)">
              {{ t('compare.viewResults') }}
            </el-button>
            <el-button
              type="danger"
              size="small"
              :disabled="!canMutateCompare"
              @click="onDeleteCompare(row)"
            >
              {{ t('compare.delete') }}
            </el-button>
          </div>
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
            teleported
            placement="bottom-start"
            :fallback-placements="selectFallbackPlacementsBottom"
            :popper-options="selectPopperOptionsNoFlip"
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
            teleported
            placement="bottom-start"
            :fallback-placements="selectFallbackPlacementsBottom"
            :popper-options="selectPopperOptionsNoFlip"
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
            teleported
            placement="bottom-start"
            :fallback-placements="selectFallbackPlacementsBottom"
            :popper-options="selectPopperOptionsNoFlip"
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
import { useAuthStore } from '../../auth/store/auth.store'
import { fetchInsightTasks } from '../../tasks/api'
import type { InsightTaskRow } from '../../tasks/types'
import {
  createCompareRun,
  deleteCompareRunRemote,
  fetchCompareRunsList,
  type CompareRunListItem,
} from '../api'
import {
  SELECT_FALLBACK_PLACEMENTS_BOTTOM,
  selectPopperOptionsNoFlip,
} from '../../../shared/ui/elementSelectPlacement'

const { t, locale } = useI18n()
const router = useRouter()
const auth = useAuthStore()
const canMutateCompare = computed(() => auth.canRetryInsightTasks.value)

const selectFallbackPlacementsBottom = SELECT_FALLBACK_PLACEMENTS_BOTTOM

type CompareTableRow = {
  id: string
  asin1: string
  asin2: string
  analysisModel: string
  creator: string
  createdAt: string
  status: 'success' | 'failed'
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
const listLoading = ref(false)

const rows = ref<CompareTableRow[]>([])

function formatTaskTime(iso: string) {
  if (!iso) return '—'
  return iso.slice(0, 19).replace('T', ' ')
}

function compareFlowStatusLabel(status: 'success' | 'failed') {
  if (status === 'success') return t('compare.flowStatus.done')
  if (status === 'failed') return t('compare.flowStatus.failed')
  return t('compare.flowStatus.analyzing')
}

function mapApiItemToRow(s: CompareRunListItem): CompareTableRow {
  const label = (s.model_label || '').trim()
  const mid = (s.model_id || '').trim()
  return {
    id: s.id,
    asin1: s.product_id_a,
    asin2: s.product_id_b,
    analysisModel: label || mid || '—',
    creator: s.creator || '—',
    createdAt: formatTaskTime(s.created_at),
    status: s.status,
    platformA: s.platform_a,
    platformB: s.platform_b,
  }
}

async function loadRows() {
  listLoading.value = true
  try {
    const res = await fetchCompareRunsList(200)
    rows.value = (res.items ?? []).map(mapApiItemToRow)
  } catch {
    rows.value = []
    ElMessage.warning(t('compare.listLoadFailed'))
  } finally {
    listLoading.value = false
  }
}

onMounted(() => {
  void loadRows()
})

watch(locale, () => {
  void loadRows()
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

function displayProviderLabel(providerId: string | null): string {
  return providerId?.trim() || 'ins_builtin'
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
  void loadRows().then(() => ElMessage.success(t('compare.refreshed')))
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

  const payload = {
    platform_a: oa.platform,
    product_id_a: oa.product_id,
    platform_b: ob.platform,
    product_id_b: ob.product_id,
    model_id: mid || null,
    model_label: modelLabel,
  }

  dialogSubmitting.value = true
  try {
    const res = await createCompareRun(payload)
    await loadRows()
    if (res.status === 'success') {
      addDialogVisible.value = false
      resetAddForm()
      page.value = 1
      ElMessage.success(t('compare.compareSaved'))
    } else {
      const msg = res.error_message || t('compare.compareFailed')
      ElMessage.warning(msg)
    }
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : t('compare.compareFailed'))
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
  try {
    await ElMessageBox.confirm(t('compare.deleteConfirm'), t('layout.logoutTitle'), {
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await deleteCompareRunRemote(row.id)
    await loadRows()
    ElMessage.success(t('compare.deleteOk'))
    if (pagedRows.value.length === 0 && page.value > 1) {
      page.value = Math.max(1, page.value - 1)
    }
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : t('compare.deleteFail'))
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

.toolbar-refresh-square {
  width: var(--el-component-size);
  min-width: var(--el-component-size);
  height: var(--el-component-size);
  padding: 0;
}

.compare-table {
  width: 100%;
}

.compare-actions {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  align-items: center;
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
