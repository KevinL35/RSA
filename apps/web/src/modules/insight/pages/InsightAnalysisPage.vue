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
        <el-button type="primary" @click="submitAddProduct">{{ t('insight.dialogConfirm') }}</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { DocumentCopy, Plus, Refresh } from '@element-plus/icons-vue'
import { insightApiConfigRows } from '../../settings/apiConfig.shared'

const { t, locale } = useI18n()

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
}

const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const pageSizeOptions = [10, 20, 50] as const

const addDialogVisible = ref(false)
const linkInputs = ref<string[]>([''])
const insightModelId = ref<string>('')

const insightModelOptions = computed(() =>
  insightApiConfigRows.value.map((row) => ({
    id: row.id,
    label: row.builtin ? t('settings.insightBuiltinModelName') : row.name,
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
    },
  ]
}

const rows = ref<InsightProductRow[]>([])

onMounted(() => {
  rows.value = buildDefaultRows(locale.value === 'zh-CN')
})

function onPageSizeChange() {
  page.value = 1
}

function tryExtractAsin(link: string): string | null {
  const m = link.match(/(?:dp|gp\/product)\/([A-Z0-9]{10})(?:\/|\?|$)/i)
  return m ? m[1].toUpperCase() : null
}

function submitAddProduct() {
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
  const modelLabel = cfg.builtin ? t('settings.insightBuiltinModelName') : cfg.name
  const zh = locale.value === 'zh-CN'
  const now = new Date().toISOString().slice(0, 16).replace('T', ' ')
  for (const link of [...links].reverse()) {
    const asin = tryExtractAsin(link) ?? '—'
    const seed = String(link.length + id.length)
    rows.value.unshift({
      imageUrl: `https://picsum.photos/seed/add-${seed}/96/96`,
      asin,
      title: link.length > 80 ? `${link.slice(0, 80)}…` : link,
      countryLabel: '—',
      priceLabel: '—',
      rating: 0,
      reviewCount: 0,
      creator: zh ? '当前用户' : 'Current user',
      createdAt: now,
      aiModel: modelLabel,
      statusLabel: zh ? '待分析' : 'Pending',
    })
  }
  addDialogVisible.value = false
  resetAddForm()
  page.value = 1
  ElMessage.success(t('insight.addProductSuccessCount', { n: links.length }))
}

const pagedRows = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return rows.value.slice(start, start + pageSize.value)
})

function onAddProduct() {
  addDialogVisible.value = true
}

async function onRefresh() {
  loading.value = true
  await new Promise((r) => setTimeout(r, 400))
  loading.value = false
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

function onViewResults(_row: InsightProductRow) {
  ElMessage.info(t('insight.viewResultsSoon'))
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
