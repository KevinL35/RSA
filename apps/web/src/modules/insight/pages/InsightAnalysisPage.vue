<template>
  <el-card class="view-card" v-loading="loading">
    <header class="page-header">
      <h2 class="page-title">{{ t('insight.title') }}</h2>
      <p class="page-subtitle">{{ t('insight.pageSubtitle') }}</p>
    </header>
    <div class="toolbar">
      <el-button type="primary" @click="onAddProduct">{{ t('insight.addProduct') }}</el-button>
      <el-button :icon="Refresh" @click="onRefresh" :loading="loading" :title="t('insight.refresh')" />
    </div>

    <el-table :data="pagedRows" stripe class="insight-table" :empty-text="t('insight.tableEmpty')">
      <el-table-column :label="t('insight.colImage')" width="76" align="center">
        <template #default="{ row }">
          <el-image :src="row.imageUrl" fit="cover" class="thumb">
            <template #error>
              <div class="thumb thumb--fallback" />
            </template>
          </el-image>
        </template>
      </el-table-column>
      <el-table-column :label="t('insight.colAsin')" min-width="150">
        <template #default="{ row }">
          <span class="asin-cell">
            <a href="#" class="asin-link" @click.prevent>{{ row.asin }}</a>
            <el-button type="primary" link class="copy-btn" @click="copyAsin(row.asin)">
              <el-icon><DocumentCopy /></el-icon>
            </el-button>
          </span>
        </template>
      </el-table-column>
      <el-table-column
        prop="title"
        :label="t('insight.colTitle')"
        min-width="200"
        show-overflow-tooltip
      />
      <el-table-column prop="countryLabel" :label="t('insight.colCountry')" width="100" />
      <el-table-column prop="priceLabel" :label="t('insight.colPrice')" width="100" />
      <el-table-column :label="t('insight.colRating')" width="168">
        <template #default="{ row }">
          <el-rate
            v-if="row.rating > 0"
            :model-value="row.rating"
            disabled
            allow-half
            show-score
            text-color="#f7ba2a"
          />
          <span v-else class="muted-rating">—</span>
        </template>
      </el-table-column>
      <el-table-column prop="reviewCount" :label="t('insight.colReviewCount')" width="110" align="right" />
      <el-table-column prop="creator" :label="t('insight.colCreator')" width="120" show-overflow-tooltip />
      <el-table-column prop="createdAt" :label="t('insight.colCreatedAt')" width="168" />
      <el-table-column prop="aiModel" :label="t('insight.colInsightModel')" width="120" show-overflow-tooltip />
      <el-table-column :label="t('insight.colStatus')" width="112">
        <template #default="{ row }">
          <span class="status-text">{{ row.statusLabel }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="t('insight.colActions')" width="168" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="onViewResults(row)">{{ t('insight.viewResults') }}</el-button>
          <el-button type="primary" link @click="onRegenerate(row)">{{ t('insight.regenerate') }}</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pager-bar">
      <div class="pager-left">
        <span class="pager-total">{{ t('insight.pagerTotal', { n: rows.length }) }}</span>
        <span class="pager-per">
          <span class="pager-per-label">{{ t('insight.pagerPerPage') }}</span>
          <el-select
            v-model="pageSize"
            class="pager-size-select"
            :teleported="false"
            @change="onPageSizeChange"
          >
            <el-option v-for="s in pageSizeOptions" :key="s" :label="String(s)" :value="s" />
          </el-select>
          <span class="pager-per-suffix">{{ t('insight.pagerItemsUnit') }}</span>
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
      :title="t('insight.dialogAddProduct')"
      width="560px"
      destroy-on-close
      @closed="resetAddForm"
    >
      <el-form label-position="top" class="add-dialog-form">
        <el-form-item required class="link-form-item">
          <template #label>
            <div class="link-field-label-row">
              <span>{{ t('insight.formLink') }}</span>
              <el-button
                type="primary"
                :icon="Plus"
                size="small"
                class="link-add-btn"
                @click="appendLinkRow"
              />
            </div>
          </template>
          <div class="link-inputs-stack">
            <div
              v-for="(_, i) in linkInputs"
              :key="i"
              class="link-input-row"
            >
              <el-input v-model="linkInputs[i]" clearable class="link-input-field" />
            </div>
          </div>
        </el-form-item>
        <el-form-item :label="t('insight.formInsightModel')" required>
          <el-select
            v-model="insightModelId"
            class="insight-model-select"
            clearable
            :teleported="false"
            :placeholder="t('insight.formInsightModelPh')"
          >
            <el-option
              v-for="opt in insightModelOptions"
              :key="opt.id"
              :label="opt.label"
              :value="opt.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialogVisible = false">{{ t('insight.dialogCancel') }}</el-button>
        <el-button type="primary" :loading="dialogSubmitting" @click="submitAddProduct">
          {{ t('insight.dialogConfirm') }}
        </el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { DocumentCopy, Plus, Refresh } from '@element-plus/icons-vue'
import type { ApiConfigRow } from '../../settings/apiConfig.shared'
import { insightApiConfigRows } from '../../settings/apiConfig.shared'
import { fetchInsightTasks } from '../../tasks/api'
import type { InsightTaskRow } from '../../tasks/types'
import { createInsightTask, postInsightTaskAnalyze, postInsightTaskFetchReviews } from '../api'

const { t, locale } = useI18n()
const router = useRouter()

type InsightProductRow = {
  imageUrl: string
  asin: string
  title: string
  countryLabel: string
  priceLabel: string
  rating: number
  reviewCount: number
  creator: string
  createdAt: string
  aiModel: string
  statusLabel: string
  /** 真实洞察任务 UUID；缺省则结果页使用 demo 数据 */
  taskId?: string
}

const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const pageSizeOptions = [10, 20, 50] as const

const addDialogVisible = ref(false)
const linkInputs = ref<string[]>([''])
const insightModelId = ref<string>('')
const dialogSubmitting = ref(false)

function insightOptionLabel(row: ApiConfigRow) {
  const name = row.builtin ? t('settings.insightBuiltinModelName') : row.name
  const m = row.model?.trim()
  return m ? `${name}-${m}` : name
}

const insightModelOptions = computed(() =>
  insightApiConfigRows.value.map((row) => ({
    id: row.id,
    label: insightOptionLabel(row),
  })),
)

function appendLinkRow() {
  linkInputs.value.push('')
}

function resetAddForm() {
  linkInputs.value = ['']
  insightModelId.value = ''
}

function buildDefaultRows(zh: boolean): InsightProductRow[] {
  return [
    {
      imageUrl: 'https://picsum.photos/seed/insight1/96/96',
      asin: 'B0XXXXTEST1',
      title: zh
        ? '示例商品标题一（用于列表展示，过长时省略号截断）'
        : 'Sample product title one (truncated with ellipsis when too long)',
      countryLabel: zh ? '美国' : 'United States',
      priceLabel: '$59.99',
      rating: 4.6,
      reviewCount: 12840,
      creator: zh ? '超级管理员' : 'Super admin',
      createdAt: '2026-03-18 14:22',
      aiModel: 'DeepSeek',
      statusLabel: zh ? '分析成功' : 'Done',
      taskId: 'demo',
    },
    {
      imageUrl: 'https://picsum.photos/seed/insight2/96/96',
      asin: 'B0XXXXTEST2',
      title: zh ? '示例商品标题二' : 'Sample product title two',
      countryLabel: zh ? '美国' : 'United States',
      priceLabel: '$24.50',
      rating: 4.2,
      reviewCount: 3201,
      creator: zh ? '分析师' : 'Analyst',
      createdAt: '2026-03-17 09:05',
      aiModel: 'DeepSeek',
      statusLabel: zh ? '分析成功' : 'Done',
      taskId: 'demo',
    },
    {
      imageUrl: 'https://picsum.photos/seed/insight3/96/96',
      asin: 'B0XXXXTEST3',
      title: zh ? '示例商品标题三' : 'Sample product title three',
      countryLabel: zh ? '英国' : 'United Kingdom',
      priceLabel: '£19.99',
      rating: 3.9,
      reviewCount: 892,
      creator: zh ? '超级管理员' : 'Super admin',
      createdAt: '2026-03-16 18:40',
      aiModel: 'DeepSeek',
      statusLabel: zh ? '分析中' : 'Running',
      taskId: 'demo',
    },
  ]
}

const rows = ref<InsightProductRow[]>([])

function taskStatusLabel(status: string) {
  const k = status as 'pending' | 'running' | 'success' | 'failed' | 'cancelled'
  if (k === 'pending' || k === 'running' || k === 'success' || k === 'failed' || k === 'cancelled') {
    return t(`insight.taskStatus.${k}`)
  }
  return status
}

function displayProviderLabel(providerId: string | null) {
  if (!providerId) return t('insight.defaultAnalysisProvider')
  const cfg = insightApiConfigRows.value.find((r) => r.id === providerId)
  return cfg ? insightOptionLabel(cfg) : providerId
}

function formatTaskTime(iso: string) {
  if (!iso) return '—'
  return iso.slice(0, 19).replace('T', ' ')
}

function mapTaskToRow(task: InsightTaskRow): InsightProductRow {
  return {
    imageUrl: `https://picsum.photos/seed/${encodeURIComponent(task.id)}/96/96`,
    asin: task.product_id,
    title: `${task.platform} · ${task.product_id}`,
    countryLabel: '—',
    priceLabel: '—',
    rating: 0,
    reviewCount: 0,
    creator: '—',
    createdAt: formatTaskTime(task.created_at),
    aiModel: displayProviderLabel(task.analysis_provider_id),
    statusLabel: taskStatusLabel(task.status),
    taskId: task.id,
  }
}

async function loadTasks() {
  loading.value = true
  try {
    const res = await fetchInsightTasks({ limit: 50 })
    rows.value = (res.items ?? []).map(mapTaskToRow)
  } catch (e) {
    const detail = e instanceof Error ? e.message : String(e)
    ElMessage.warning(`${t('insight.listLoadFailed')} — ${detail}`)
    rows.value = buildDefaultRows(locale.value === 'zh-CN')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void loadTasks()
})

watch(locale, () => {
  void loadTasks()
})

function onPageSizeChange() {
  page.value = 1
}

function tryExtractAsin(link: string): string | null {
  const m = link.match(/(?:dp|gp\/product)\/([A-Z0-9]{10})(?:\/|\?|$)/i)
  return m ? m[1].toUpperCase() : null
}

async function submitAddProduct() {
  const links = linkInputs.value.map((s) => s.trim()).filter(Boolean)
  if (links.length === 0) {
    ElMessage.warning(t('insight.addProductNeedLink'))
    return
  }
  const id = insightModelId.value
  if (!id) {
    ElMessage.warning(t('insight.addProductNeedModel'))
    return
  }
  const cfg = insightApiConfigRows.value.find((r) => r.id === id)
  if (!cfg) {
    ElMessage.warning(t('insight.insightModelMissing'))
    return
  }

  dialogSubmitting.value = true
  let ok = 0
  try {
    for (const link of links) {
      const productId = tryExtractAsin(link) ?? link.trim().slice(0, 256)
      if (!productId) {
        ElMessage.warning(t('insight.productIdInvalid'))
        continue
      }
      const task = await createInsightTask({
        platform: 'amazon',
        product_id: productId,
        analysis_provider_id: id,
      })
      await postInsightTaskFetchReviews(task.id)
      await postInsightTaskAnalyze(task.id)
      ok++
    }
    if (ok === 0) {
      return
    }
    addDialogVisible.value = false
    resetAddForm()
    page.value = 1
    ElMessage.success(t('insight.addProductSuccessCount', { n: ok }))
    await loadTasks()
  } catch (e) {
    ElMessage.error(
      e instanceof Error ? `${t('insight.addProductPipelineFailed')}: ${e.message}` : t('insight.addProductPipelineFailed'),
    )
  } finally {
    dialogSubmitting.value = false
  }
}

const pagedRows = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return rows.value.slice(start, start + pageSize.value)
})

function onAddProduct() {
  addDialogVisible.value = true
}

async function onRefresh() {
  await loadTasks()
  ElMessage.success(t('insight.refreshed'))
}

async function copyAsin(asin: string) {
  try {
    await navigator.clipboard.writeText(asin)
    ElMessage.success(t('insight.copyAsinOk'))
  } catch {
    ElMessage.warning(t('insight.copyAsinFail'))
  }
}

function onViewResults(row: InsightProductRow) {
  const tid = row.taskId ?? 'demo'
  void router.push({
    path: `/insight-analysis/result/${encodeURIComponent(tid)}`,
    query: {
      title: row.title,
      asin: row.asin,
      country: row.countryLabel,
      price: row.priceLabel,
      rating: row.rating > 0 ? String(row.rating) : '',
      reviews: String(row.reviewCount),
      model: row.aiModel,
      analyzedAt: row.createdAt,
    },
  })
}

function onRegenerate(_row: InsightProductRow) {
  ElMessage.info(t('insight.regenerateSoon'))
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

.insight-table {
  width: 100%;
}

.thumb {
  width: 48px;
  height: 48px;
  border-radius: 6px;
  display: block;
}

.thumb--fallback {
  background: linear-gradient(135deg, #e2e8f0 0%, #cbd5e1 100%);
}

.asin-cell {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.asin-link {
  color: var(--el-color-primary);
  text-decoration: none;
  font-weight: 500;
}

.asin-link:hover {
  text-decoration: underline;
}

.copy-btn {
  padding: 0 4px;
  min-height: auto;
}

.status-text {
  font-size: 13px;
  color: var(--el-text-color-regular);
}

.muted-rating {
  color: var(--el-text-color-placeholder);
  font-size: 14px;
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

.pager-nav:deep(.btn-prev:disabled),
.pager-nav:deep(.btn-next:disabled) {
  background-color: var(--el-fill-color-light);
}

.add-dialog-form {
  padding-top: 4px;
}

.link-form-item :deep(.el-form-item__label) {
  display: flex;
  width: 100%;
  padding-right: 0;
  box-sizing: border-box;
}

.link-field-label-row {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.link-add-btn {
  flex-shrink: 0;
  min-width: 28px;
  width: 28px;
  height: 28px;
  padding: 0;
  border-radius: 4px;
}

.link-inputs-stack {
  width: 100%;
}

.link-input-row {
  margin-bottom: 10px;
}

.link-input-row:last-child {
  margin-bottom: 0;
}

.link-input-field {
  width: 100%;
}

.insight-model-select {
  width: 100%;
}
</style>
