<template>
  <el-card class="view-card" v-loading="loading">
    <header class="page-header">
      <h2 class="page-title">{{ t('insight.title') }}</h2>
      <p class="page-subtitle">{{ t('insight.desc') }}</p>
    </header>
    <div class="toolbar">
      <div class="toolbar-right">
        <el-button type="primary" @click="onAddProduct">{{ t('insight.addProduct') }}</el-button>
        <el-button
          type="primary"
          :disabled="!canMutateInsightTasks"
          @click="onUploadReviews"
        >
          {{ t('insight.uploadReviews') }}
        </el-button>
        <el-button
          class="toolbar-refresh-square"
          :icon="Refresh"
          @click="onRefresh"
          :loading="loading"
          :title="t('insight.refresh')"
        />
      </div>
    </div>

    <el-table :data="pagedRows" stripe class="insight-table" :empty-text="t('insight.tableEmpty')">
      <el-table-column :label="t('insight.colImage')" width="76" align="center">
        <template #default="{ row }">
          <el-image
            :key="`${row.taskId ?? row.asin}-${row.imageUrl}`"
            :src="row.imageUrl"
            fit="contain"
            class="thumb"
            referrerpolicy="no-referrer"
            @load="insightThumbLoadHandler(row)"
            @error="() => onProductImageError(row)"
          >
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
        :label="t('insight.colPrice')"
        width="108"
        show-overflow-tooltip
      >
        <template #default="{ row }">
          <span class="status-text">{{ row.priceLabel }}</span>
        </template>
      </el-table-column>
      <el-table-column
        :label="t('insight.colDictionaryVertical')"
        width="120"
        show-overflow-tooltip
      >
        <template #default="{ row }">
          <span class="status-text">{{ row.dictionaryVerticalLabel }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="t('insight.colReviewStatus')" width="112">
        <template #default="{ row }">
          <span class="status-text">{{ row.reviewStatusLabel }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="t('insight.colInsightStatus')" width="112">
        <template #default="{ row }">
          <span class="status-text">{{ row.statusLabel }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="creator" :label="t('insight.colCreator')" width="120" show-overflow-tooltip />
      <el-table-column prop="createdAt" :label="t('insight.colCreatedAt')" width="168" />
      <el-table-column :label="t('insight.colActions')" min-width="260" fixed="right" align="left" header-align="left">
        <template #default="{ row }">
          <div class="insight-actions-row">
            <el-button
              type="primary"
              size="small"
              :disabled="downloadReviewsDisabled(row)"
              :loading="downloadReviewingId === row.taskId"
              @click="onDownloadReviews(row)"
            >
              {{ t('insight.downloadReviews') }}
            </el-button>
            <el-button
              type="primary"
              size="small"
              :disabled="viewResultsDisabled(row)"
              :title="viewResultsDisabledReason(row)"
              @click="onViewResults(row)"
            >
              {{ t('insight.viewResults') }}
            </el-button>
            <el-button
              type="danger"
              size="small"
              :disabled="deleteInsightDisabled(row)"
              :loading="deletingTaskId === row.taskId"
              @click="onDeleteInsight(row)"
            >
              {{ t('insight.delete') }}
            </el-button>
          </div>
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
            teleported
            placement="bottom-start"
            :fallback-placements="selectFallbackPlacementsBottom"
            :popper-options="selectPopperOptionsNoFlip"
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
        <el-form-item :label="t('insight.formDictionaryVertical')" required>
          <el-select
            v-model="dictionaryVerticalId"
            class="insight-model-select"
            teleported
            placement="bottom-start"
            :fallback-placements="selectFallbackPlacementsBottom"
            :popper-options="selectPopperOptionsNoFlip"
          >
            <el-option
              v-for="opt in dictionaryVerticalOptions"
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

    <el-dialog
      v-model="uploadDialogVisible"
      :title="t('insight.dialogUploadReviews')"
      width="580px"
      class="upload-reviews-dialog"
      destroy-on-close
      align-center
      @closed="resetUploadForm"
    >
      <p class="upload-reviews-intro">{{ t('insight.uploadReviewsIntro') }}</p>

      <div
        class="upload-template-strip"
        role="region"
        :aria-label="t('insight.uploadTemplateStripLabel')"
      >
        <div class="upload-template-strip-left">
          <el-icon class="upload-template-strip-icon"><Download /></el-icon>
          <span class="upload-template-strip-text">{{ t('insight.uploadTemplateStripLabel') }}</span>
        </div>
        <el-button
          link
          type="primary"
          class="upload-template-download-btn"
          @click="onDownloadReviewTemplate"
        >
          {{ t('insight.uploadTemplateDownload') }}
        </el-button>
      </div>

      <el-form label-position="top" class="upload-reviews-form">
        <el-form-item :label="t('insight.formProductIdUpload')">
          <el-input
            v-model="uploadLinkInput"
            clearable
            :placeholder="t('insight.formProductIdUploadPlaceholder')"
          />
        </el-form-item>
        <el-form-item :label="t('insight.formDictionaryVertical')" required>
          <el-select
            v-model="uploadDictionaryVerticalId"
            class="insight-model-select"
            :teleported="true"
            placement="bottom-start"
            :fallback-placements="selectFallbackPlacementsBottom"
            :popper-options="selectPopperOptionsNoFlip"
          >
            <el-option
              v-for="opt in dictionaryVerticalOptions"
              :key="opt.id"
              :label="opt.label"
              :value="opt.id"
            />
          </el-select>
        </el-form-item>
        <div class="upload-file-section-label">{{ t('insight.uploadFileSectionLabel') }}</div>
        <div class="upload-file-zone">
          <el-upload
            ref="uploadExcelRef"
            class="upload-file-inner"
            :auto-upload="false"
            :limit="1"
            :show-file-list="false"
            accept=".xlsx,.xls,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            :on-change="onUploadExcelChange"
            :on-exceed="onUploadExcelExceed"
          >
            <div class="upload-file-trigger-row">
              <span
                class="upload-file-status"
                :class="{ 'upload-file-status--placeholder': !uploadExcelFile }"
              >
                {{ uploadExcelDisplayName }}
              </span>
            </div>
          </el-upload>
        </div>
        <p class="upload-file-hint">{{ t('insight.uploadFileFormatHint') }}</p>
      </el-form>
      <template #footer>
        <div class="upload-reviews-footer">
          <el-button @click="uploadDialogVisible = false">{{ t('insight.dialogCancel') }}</el-button>
          <el-button type="primary" :loading="uploadSubmitting" @click="submitUploadReviews">
            {{ t('insight.uploadStartImport') }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { genFileId } from 'element-plus'
import type { UploadFile, UploadInstance, UploadRawFile } from 'element-plus'
import { DocumentCopy, Download, Plus, Refresh } from '@element-plus/icons-vue'
import { deleteInsightTask, fetchInsightTasks } from '../../tasks/api'
import type { InsightTaskRow } from '../../tasks/types'
import {
  extractAsinFromAmazonUrl,
  isLikelyAmazonAsin,
  looksLikeAmazonProductUrl,
  resolveProductIdForUploadReviews,
} from '../../../shared/utils/amazonAsin'
import { downloadReviewImportTemplate, downloadReviewsExcel } from '../../../shared/utils/excelDownload'

const BUILTIN_ANALYSIS_PROVIDER_ID = 'ins_builtin'
import {
  createInsightTask,
  fetchInsightTaskReviews,
  postInsightTaskAnalyze,
  postInsightTaskFetchReviews,
  postInsightTaskImportReviews,
} from '../api'
import { getStoredUsername, useAuthStore } from '../../auth/store/auth.store'
import type { DictionaryVerticalItem } from '../../dictionary/api'
import { fetchDictionaryVerticals } from '../../dictionary/api'
import {
  SELECT_FALLBACK_PLACEMENTS_BOTTOM,
  selectPopperOptionsNoFlip,
} from '../../../shared/ui/elementSelectPlacement'

const { t, locale } = useI18n()
const router = useRouter()
const auth = useAuthStore()
const canMutateInsightTasks = computed(() => auth.canRetryInsightTasks.value)

const selectFallbackPlacementsBottom = SELECT_FALLBACK_PLACEMENTS_BOTTOM

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
  /** 透传给结果页 meta 的模型描述（当前固定内置） */
  aiModel: string
  reviewStatus: 'fetching' | 'completed' | 'failed'
  reviewStatusLabel: string
  statusLabel: string
  /** insight_tasks.status，用于操作按钮禁用逻辑 */
  taskStatus?: string
  /** AI 智能分析是否已生成（dashboard 与查看结果按钮的解锁前置） */
  aiSummaryReady?: boolean
  /**
   * 列表缩略图重试阶段：extra 图 → 主 CDN → 备用 CDN → 占位。
   * Amazon 对无效 ASIN 常返回 200 + 1×1 GIF，需配合 @load 尺寸判断。
   */
  imageThumbPhase?: 'extra' | 'amazon_primary' | 'amazon_fallback' | 'exhausted'
  /** 洞察任务 UUID */
  taskId?: string
  dictionaryVerticalLabel: string
}

const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const pageSizeOptions = [10, 20, 50] as const

const dictionaryVerticals = ref<DictionaryVerticalItem[]>([])
const DEFAULT_VERTICAL_ID = 'electronics'
const dictionaryVerticalId = ref(DEFAULT_VERTICAL_ID)
const uploadDictionaryVerticalId = ref(DEFAULT_VERTICAL_ID)

const addDialogVisible = ref(false)
const linkInputs = ref<string[]>([''])
const dialogSubmitting = ref(false)
const uploadDialogVisible = ref(false)
const uploadLinkInput = ref('')
const uploadExcelFile = ref<File | null>(null)
const uploadExcelRef = ref<UploadInstance | null>(null)
const uploadSubmitting = ref(false)
/** 与后端 import-reviews 一致 */
const UPLOAD_REVIEW_MAX_BYTES = 10 * 1024 * 1024
const downloadReviewingId = ref<string | null>(null)
const deletingTaskId = ref<string | null>(null)

const REVIEW_EXPORT_COLUMNS = [
  { label: '平台', key: 'platform' },
  { label: 'ASIN', key: 'product_id' },
  { label: '发布时间', key: 'reviewed_at' },
  { label: '标题', key: 'title' },
  { label: '评论', key: 'raw_text' },
] as const

const dictionaryVerticalOptions = computed(() => {
  if (dictionaryVerticals.value.length > 0) {
    return dictionaryVerticals.value.map((v) => ({
      id: v.id,
      label: locale.value === 'zh-CN' ? v.label_zh : v.label_en,
    }))
  }
  return [{ id: 'electronics', label: locale.value === 'zh-CN' ? '电子产品' : 'Electronics' }]
})

function verticalLabelForTask(vid: string | null | undefined): string {
  const id = (vid || DEFAULT_VERTICAL_ID).trim() || DEFAULT_VERTICAL_ID
  const v = dictionaryVerticals.value.find((x) => x.id === id)
  if (!v) return id
  return locale.value === 'zh-CN' ? v.label_zh : v.label_en
}

async function ensureDictionaryVerticals() {
  if (dictionaryVerticals.value.length > 0) return
  try {
    const res = await fetchDictionaryVerticals()
    dictionaryVerticals.value = res.items ?? []
  } catch {
    dictionaryVerticals.value = []
  }
}

const uploadExcelDisplayName = computed(() =>
  uploadExcelFile.value?.name ?? t('insight.uploadFileClickToChoose'),
)

function isAllowedReviewExcelFileName(name: string): boolean {
  const lower = name.toLowerCase()
  return lower.endsWith('.xlsx') || lower.endsWith('.xls')
}

async function onDownloadReviewTemplate() {
  try {
    await downloadReviewImportTemplate()
    ElMessage.success(t('insight.uploadTemplateDownloadOk'))
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    ElMessage.error(`${t('insight.uploadTemplateDownloadFail')}: ${msg}`)
  }
}

function appendLinkRow() {
  linkInputs.value.push('')
}

function resetAddForm() {
  linkInputs.value = ['']
  dictionaryVerticalId.value = DEFAULT_VERTICAL_ID
}

const rows = ref<InsightProductRow[]>([])

/** 非真实 ASIN 或双 CDN 均无效时的列表占位（避免 Amazon 200+1×1 GIF 看起来像「没图」） */
const INSIGHT_LIST_IMAGE_PLACEHOLDER =
  'data:image/svg+xml,' +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80" viewBox="0 0 80 80"><rect fill="#ececec" width="80" height="80"/><g fill="#b0b0b0"><circle cx="40" cy="34" r="10"/><path d="M26 58c0-8 6-14 14-14s14 6 14 14v2H26v-2z"/></g></svg>',
  )

function isLikelyHttpImageUrl(s: string): boolean {
  const t = s.trim().toLowerCase()
  return t.startsWith('https://') || t.startsWith('http://') || t.startsWith('data:image/')
}

/** 美国站主图：先试 m.media-amazon，失败由 @error / 1×1 检测切 ssl-images-na */
function amazonUsImageUrlPrimary(productId: string): string {
  const asin = encodeURIComponent(productId.trim())
  return `https://m.media-amazon.com/images/P/${asin}.01._AC_SL80_.jpg`
}

function amazonUsImageUrlFallback(productId: string): string {
  const asin = encodeURIComponent(productId.trim())
  return `https://images-na.ssl-images-amazon.com/images/P/${asin}.01._SX80_.jpg`
}

function bumpInsightListImage(row: InsightProductRow) {
  const asin = row.asin.trim()
  const phase = row.imageThumbPhase ?? 'exhausted'
  switch (phase) {
    case 'extra':
      if (isLikelyAmazonAsin(asin)) {
        row.imageUrl = amazonUsImageUrlPrimary(asin)
        row.imageThumbPhase = 'amazon_primary'
      } else {
        row.imageUrl = INSIGHT_LIST_IMAGE_PLACEHOLDER
        row.imageThumbPhase = 'exhausted'
      }
      break
    case 'amazon_primary':
      row.imageUrl = amazonUsImageUrlFallback(asin)
      row.imageThumbPhase = 'amazon_fallback'
      break
    case 'amazon_fallback':
      row.imageUrl = INSIGHT_LIST_IMAGE_PLACEHOLDER
      row.imageThumbPhase = 'exhausted'
      break
    default:
      break
  }
}

function onProductImageError(row: InsightProductRow) {
  bumpInsightListImage(row)
}

const insightThumbLoadHandlers = new WeakMap<InsightProductRow, (e: Event) => void>()

function insightThumbLoadHandler(row: InsightProductRow) {
  let fn = insightThumbLoadHandlers.get(row)
  if (!fn) {
    fn = (e: Event) => {
      const el = e.target as HTMLImageElement | null
      if (!el) return
      if (el.naturalWidth > 1 && el.naturalHeight > 1) return
      bumpInsightListImage(row)
    }
    insightThumbLoadHandlers.set(row, fn)
  }
  return fn
}

/** 洞察状态展示：分析中 / 已完成 / 失败。
 * 注意：即使后端 status='success'，只要 AI 智能分析尚未生成完成，仍展示「分析中」。
 */
function flowInsightStatusLabel(status: string, aiSummaryReady?: boolean): string {
  const key = classifyInsightFlowStatus(status, aiSummaryReady)
  return t(`insight.flowStatus.${key}`)
}

function classifyInsightFlowStatus(
  status: string,
  aiSummaryReady?: boolean,
): 'analyzing' | 'done' | 'failed' {
  if (status === 'failed' || status === 'cancelled') return 'failed'
  if (status === 'success') {
    return aiSummaryReady ? 'done' : 'analyzing'
  }
  return 'analyzing'
}

function displayProviderLabel(providerId: string | null): string {
  return providerId?.trim() || BUILTIN_ANALYSIS_PROVIDER_ID
}

function formatTaskTime(iso: string) {
  if (!iso) return '—'
  return iso.slice(0, 19).replace('T', ' ')
}

function reviewStatusFromTask(task: InsightTaskRow): 'fetching' | 'completed' | 'failed' {
  if (task.status === 'failed') {
    const fs = (task.failure_stage || '').trim().toLowerCase()
    if (fs === 'fetch') return 'failed'
    return 'completed'
  }
  if (task.status === 'success') return 'completed'
  return 'fetching'
}

function mapTaskToRow(task: InsightTaskRow): InsightProductRow {
  const rs = reviewStatusFromTask(task)
  const full = displayProviderLabel(task.analysis_provider_id)
  const pid = task.product_id.trim()
  const useAmazonThumb = isLikelyAmazonAsin(pid)
  const snap = task.product_snapshot
  const snapTitle = typeof snap?.title === 'string' ? snap.title.trim() : ''
  const snapImg = typeof snap?.image_url === 'string' ? snap.image_url.trim() : ''
  const snapPrice = typeof snap?.price_display === 'string' ? snap.price_display.trim() : ''
  let imageUrl: string
  let imageThumbPhase: InsightProductRow['imageThumbPhase']
  if (snapImg) {
    imageUrl = snapImg
    imageThumbPhase = 'exhausted'
  } else if (useAmazonThumb) {
    imageUrl = amazonUsImageUrlPrimary(pid)
    imageThumbPhase = 'amazon_primary'
  } else {
    imageUrl = INSIGHT_LIST_IMAGE_PLACEHOLDER
    imageThumbPhase = 'exhausted'
  }
  const aiReady = !!(task.ai_summary?.text && task.ai_summary.text.trim())
  return {
    imageUrl,
    imageThumbPhase,
    asin: task.product_id,
    title: snapTitle || task.product_id,
    countryLabel: '—',
    priceLabel: snapPrice || '—',
    rating: 0,
    reviewCount: 0,
    creator: creatorForTask(task),
    createdAt: formatTaskTime(task.created_at),
    aiModel: full,
    reviewStatus: rs,
    reviewStatusLabel: reviewStatusLabel(rs),
    statusLabel: flowInsightStatusLabel(task.status, aiReady),
    taskStatus: task.status,
    aiSummaryReady: aiReady,
    taskId: task.id,
    dictionaryVerticalLabel: verticalLabelForTask(task.dictionary_vertical_id),
  }
}

/** 列表创建人：优先库内 created_by，否则当前登录名，再否则按角色占位 */
function creatorForTask(task: InsightTaskRow): string {
  const fromDb = typeof task.created_by === 'string' ? task.created_by.trim() : ''
  if (fromDb) return fromDb
  return currentCreatorLabel()
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

function reviewStatusLabel(status: 'fetching' | 'completed' | 'failed') {
  return t(`insight.reviewStatus.${status}`)
}

function pickFirstString(items: Array<unknown>): string | null {
  for (const x of items) {
    if (typeof x === 'string') {
      const s = x.trim()
      if (s) return s
    }
  }
  return null
}

function parseCountryLabel(raw: string | null): string {
  if (!raw) return '—'
  const v = raw.trim()
  if (!v) return '—'
  const low = v.toLowerCase()
  if (low === 'us' || low === 'usa') return 'United States'
  if (low === 'uk' || low === 'gb') return 'United Kingdom'
  return v
}

function parsePriceLabel(raw: string | null): string {
  if (!raw) return '—'
  const s = raw.trim()
  return s || '—'
}

function avgRating(items: Array<{ rating?: number | null }>): number {
  const nums = items.map((x) => x.rating).filter((x): x is number => typeof x === 'number' && Number.isFinite(x))
  if (nums.length === 0) return 0
  const val = nums.reduce((a, b) => a + b, 0) / nums.length
  return Math.round(val * 10) / 10
}

type ReviewExtra = Record<string, unknown>

function pickFromExtra(extraList: ReviewExtra[], keys: string[]): string | null {
  for (const extra of extraList) {
    const found = pickFirstString(keys.map((k) => (extra[k] as string | undefined) ?? ''))
    if (found) return found
  }
  return null
}

/** 同时拉取多任务 reviews（各 up to 20000 条）易打满 Supabase / 触发 502，分批并发。 */
const HYDRATE_REVIEWS_CONCURRENCY = 3
const HYDRATE_REVIEWS_RETRIES = 3

function delay(ms: number) {
  return new Promise<void>((r) => setTimeout(r, ms))
}

async function fetchInsightTaskReviewsWithRetry(taskId: string, limit: number) {
  let last: unknown
  for (let attempt = 0; attempt < HYDRATE_REVIEWS_RETRIES; attempt++) {
    try {
      return await fetchInsightTaskReviews(taskId, limit)
    } catch (e) {
      last = e
      if (attempt < HYDRATE_REVIEWS_RETRIES - 1) {
        await delay(350 * (attempt + 1))
      }
    }
  }
  throw last
}

async function hydrateRowsWithReviewStats(taskRows: InsightTaskRow[]) {
  const byId = new Map<string, InsightProductRow>()
  for (const r of rows.value) {
    if (r.taskId) byId.set(r.taskId, r)
  }

  async function hydrateOne(task: InsightTaskRow) {
    try {
      const res = await fetchInsightTaskReviewsWithRetry(task.id, 20000)
      const row = byId.get(task.id)
      if (!row) return
      const items = res.items ?? []
      const extras = items
        .map((x) => ((x as unknown as { extra?: ReviewExtra | null }).extra ?? null))
        .filter((x): x is ReviewExtra => !!x && typeof x === 'object')

      const title = pickFirstString([
        pickFromExtra(extras, ['productTitle', 'product_title', 'title', 'name']) ?? '',
        row.title,
      ])
      const rawExtraImg = pickFromExtra(extras, [
        'productImage',
        'product_image',
        'image',
        'imageUrl',
        'image_url',
      ])
      const extraImage =
        rawExtraImg && isLikelyHttpImageUrl(rawExtraImg) ? rawExtraImg.trim() : null
      const image = pickFirstString([extraImage ?? '', row.imageUrl])
      const country = parseCountryLabel(
        pickFromExtra(extras, ['country', 'marketplace', 'site', 'region']) ??
          (task.platform === 'amazon' ? 'United States' : ''),
      )
      const rawPrice = pickFromExtra(extras, [
        'price',
        'productPrice',
        'product_price',
        'finalPrice',
        'price_display',
      ])

      row.title = title ?? row.title
      row.imageUrl = image ?? row.imageUrl
      if (extraImage) {
        row.imageThumbPhase = 'extra'
      }
      row.countryLabel = country
      // 评论 extra 里通常没有商品价：勿用「空」覆盖 product_snapshot 已展示的售价
      if (rawPrice && rawPrice.trim()) {
        row.priceLabel = parsePriceLabel(rawPrice)
      }
      row.rating = avgRating(items)
      row.reviewCount = items.length
      const fs = (task.failure_stage || '').trim().toLowerCase()
      if (items.length > 0) {
        row.reviewStatus = 'completed'
      } else if (task.status === 'failed' && fs === 'fetch') {
        row.reviewStatus = 'failed'
      } else {
        row.reviewStatus = 'fetching'
      }
      row.reviewStatusLabel = reviewStatusLabel(row.reviewStatus)
      row.statusLabel = flowInsightStatusLabel(task.status, row.aiSummaryReady)
    } catch {
      // Ignore per-row hydration errors to keep list render resilient.
    }
  }

  for (let i = 0; i < taskRows.length; i += HYDRATE_REVIEWS_CONCURRENCY) {
    const chunk = taskRows.slice(i, i + HYDRATE_REVIEWS_CONCURRENCY)
    await Promise.all(chunk.map((task) => hydrateOne(task)))
  }
}

async function loadTasks(skipAutoRefresh = false) {
  loading.value = true
  await ensureDictionaryVerticals()
  try {
    const res = await fetchInsightTasks({ limit: 50 })
    const taskRows = res.items ?? []
    rows.value = taskRows.map(mapTaskToRow)
    await hydrateRowsWithReviewStats(taskRows)
    if (!skipAutoRefresh) {
      schedulePendingAiSummaryRefresh()
    }
  } catch (e) {
    const detail = e instanceof Error ? e.message : String(e)
    ElMessage.warning(`${t('insight.listLoadFailed')} — ${detail}`)
    rows.value = []
  } finally {
    loading.value = false
  }
}

/**
 * 列表里若存在「success 但 AI 摘要还没生成」的任务，每 6 秒自动轻量刷一次列表，
 * 直到所有 success 行的 ai_summary 都就绪或视图离开；用户无需手点刷新。
 */
const AI_SUMMARY_LIST_POLL_INTERVAL_MS = 6000
let aiSummaryListPollTimer: number | null = null

function clearPendingAiSummaryRefresh() {
  if (aiSummaryListPollTimer != null) {
    window.clearTimeout(aiSummaryListPollTimer)
    aiSummaryListPollTimer = null
  }
}

function hasSuccessWithoutAiSummary(): boolean {
  return rows.value.some((r) => r.taskStatus === 'success' && r.aiSummaryReady !== true)
}

function schedulePendingAiSummaryRefresh() {
  clearPendingAiSummaryRefresh()
  if (!hasSuccessWithoutAiSummary()) return
  aiSummaryListPollTimer = window.setTimeout(() => {
    aiSummaryListPollTimer = null
    void loadTasks()
  }, AI_SUMMARY_LIST_POLL_INTERVAL_MS)
}

onMounted(() => {
  void loadTasks()
})

onBeforeUnmount(() => {
  clearPendingAiSummaryRefresh()
})

watch(locale, () => {
  void loadTasks()
})

function onPageSizeChange() {
  page.value = 1
}

function downloadReviewsDisabled(row: InsightProductRow): boolean {
  const tid = row.taskId
  return !tid || row.reviewStatus !== 'completed'
}

function deleteInsightDisabled(row: InsightProductRow): boolean {
  const tid = row.taskId
  return !canMutateInsightTasks.value || !tid
}

async function onDeleteInsight(row: InsightProductRow) {
  const tid = row.taskId
  if (!tid || !canMutateInsightTasks.value) return
  try {
    await ElMessageBox.confirm(t('insight.deleteConfirm'), t('insight.deleteTitle'), {
      type: 'warning',
      confirmButtonText: t('insight.dialogConfirm'),
      cancelButtonText: t('insight.dialogCancel'),
    })
  } catch {
    return
  }
  deletingTaskId.value = tid
  try {
    await deleteInsightTask(tid)
    ElMessage.success(t('insight.deleteOk'))
    await loadTasks()
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    ElMessage.error(`${t('insight.deleteFail')}: ${msg}`)
  } finally {
    deletingTaskId.value = null
  }
}

async function onDownloadReviews(row: InsightProductRow) {
  const tid = row.taskId
  if (!tid) {
    ElMessage.warning(t('insight.downloadReviewsNoTask'))
    return
  }
  downloadReviewingId.value = tid
  try {
    const res = await fetchInsightTaskReviews(tid)
    const items = res.items ?? []
    if (items.length === 0) {
      ElMessage.warning(t('insight.downloadReviewsEmpty'))
      return
    }
    const asin = (res.product_id || row.asin || 'product').replace(/[^\w-]/g, '_')
    const shortId = tid.slice(0, 8)
    const filename = `reviews_${asin}_${shortId}.xlsx`
    const exportRows = items.map((item) => {
      const row: Record<string, unknown> = {}
      for (const col of REVIEW_EXPORT_COLUMNS) {
        row[col.label] = (item as Record<string, unknown>)[col.key] ?? ''
      }
      return row
    })
    await downloadReviewsExcel(
      filename,
      exportRows,
      REVIEW_EXPORT_COLUMNS.map((c) => c.label),
    )
    ElMessage.success(t('insight.downloadReviewsOk', { n: items.length }))
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    ElMessage.error(`${t('insight.downloadReviewsFail')}: ${msg}`)
  } finally {
    downloadReviewingId.value = null
  }
}

async function submitAddProduct() {
  const links = linkInputs.value.map((s) => s.trim()).filter(Boolean)
  if (links.length === 0) {
    ElMessage.warning(t('insight.addProductNeedLink'))
    return
  }
  const dvid = dictionaryVerticalId.value
  if (!dvid) {
    ElMessage.warning(t('insight.needDictionaryVertical'))
    return
  }

  dialogSubmitting.value = true
  let ok = 0
  const createdTaskIds: string[] = []
  try {
    for (const link of links) {
      const trimmed = link.trim()
      const fromUrl = extractAsinFromAmazonUrl(trimmed)
      if (looksLikeAmazonProductUrl(trimmed) && !fromUrl) {
        ElMessage.warning(t('insight.linkMissingAsin'))
        continue
      }
      const productId = fromUrl ?? trimmed.slice(0, 256)
      if (!productId) {
        ElMessage.warning(t('insight.productIdInvalid'))
        continue
      }
      const task = await createInsightTask({
        platform: 'amazon',
        product_id: productId,
        analysis_provider_id: BUILTIN_ANALYSIS_PROVIDER_ID,
        dictionary_vertical_id: dvid,
      })
      createdTaskIds.push(task.id)
      ok++
    }
    if (ok === 0) {
      return
    }
    addDialogVisible.value = false
    resetAddForm()
    page.value = 1
    ElMessage.success(t('insight.addProductSuccessCount', { n: ok }))
    await loadTasks(true)
    // 按阶段刷新：添加成功 -> 抓评完成 -> 分析完成
    void (async () => {
      const failed: string[] = []
      const fetchedTaskIds: string[] = []
      await Promise.all(
        createdTaskIds.map(async (taskId) => {
          try {
            await postInsightTaskFetchReviews(taskId)
            fetchedTaskIds.push(taskId)
          } catch (err) {
            const msg = err instanceof Error ? err.message : String(err)
            failed.push(msg)
          }
        }),
      )
      await loadTasks(true)

      await Promise.all(
        fetchedTaskIds.map(async (taskId) => {
          try {
            await postInsightTaskAnalyze(taskId)
          } catch (err) {
            const msg = err instanceof Error ? err.message : String(err)
            failed.push(msg)
          }
        }),
      )
      await loadTasks(true)

      if (failed.length > 0) {
        ElMessage.warning(`${t('insight.addProductPipelineFailed')}: ${failed[0]}`)
      }
    })()
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

function onUploadReviews() {
  uploadDialogVisible.value = true
}

function resetUploadForm() {
  uploadLinkInput.value = ''
  uploadDictionaryVerticalId.value = DEFAULT_VERTICAL_ID
  uploadExcelFile.value = null
  uploadExcelRef.value?.clearFiles()
}

function onUploadExcelChange(uploadFile: UploadFile) {
  uploadExcelFile.value = uploadFile.raw ?? null
}

function onUploadExcelExceed(files: File[]) {
  uploadExcelRef.value?.clearFiles()
  const f = files[0]
  if (!f) return
  const raw = f as UploadRawFile
  raw.uid = genFileId()
  uploadExcelRef.value?.handleStart(raw)
}

async function submitUploadReviews() {
  const trimmed = uploadLinkInput.value.trim()
  const resolved = resolveProductIdForUploadReviews(trimmed)
  if (!resolved.ok) {
    if (resolved.reason === 'url_no_asin') {
      ElMessage.warning(t('insight.linkMissingAsin'))
    } else {
      ElMessage.warning(t('insight.uploadProductIdInvalidFormat'))
    }
    return
  }
  const productId = resolved.productId
  const file = uploadExcelFile.value
  if (!file) {
    ElMessage.warning(t('insight.uploadNeedFile'))
    return
  }
  if (!isAllowedReviewExcelFileName(file.name)) {
    ElMessage.warning(t('insight.uploadNeedFile'))
    return
  }
  if (file.size > UPLOAD_REVIEW_MAX_BYTES) {
    ElMessage.warning(t('insight.uploadFileTooLarge'))
    return
  }

  uploadSubmitting.value = true
  try {
    const dvid = uploadDictionaryVerticalId.value
    if (!dvid) {
      ElMessage.warning(t('insight.needDictionaryVertical'))
      return
    }
    const task = await createInsightTask({
      platform: 'amazon',
      product_id: productId,
      analysis_provider_id: BUILTIN_ANALYSIS_PROVIDER_ID,
      dictionary_vertical_id: dvid,
    })
    const taskId = task.id
    const imp = await postInsightTaskImportReviews(taskId, file)
    const n = imp.reviews_inserted ?? 0
    uploadDialogVisible.value = false
    resetUploadForm()
    page.value = 1
    ElMessage.success(t('insight.uploadReviewsSuccess', { n }))
    await loadTasks()
    try {
      await postInsightTaskAnalyze(taskId)
      await loadTasks()
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      ElMessage.warning(`${t('insight.uploadReviewsFail')}: ${msg}`)
      await loadTasks()
    }
  } catch (e) {
    ElMessage.error(
      e instanceof Error ? `${t('insight.uploadReviewsFail')}: ${e.message}` : t('insight.uploadReviewsFail'),
    )
  } finally {
    uploadSubmitting.value = false
  }
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

function viewResultsDisabled(row: InsightProductRow): boolean {
  const s = row.taskStatus
  if (s === 'pending' || s === 'running') return true
  /** 任务已 success 但 AI 智能分析尚未生成完成 → 不允许查看结果，避免看到「无 AI 摘要 + 规则要点」的中间态 */
  if (s === 'success' && row.aiSummaryReady !== true) return true
  return false
}

function viewResultsDisabledReason(row: InsightProductRow): string | undefined {
  const s = row.taskStatus
  if (s === 'pending' || s === 'running') return t('insight.viewResultsDisabledHint')
  if (s === 'success' && row.aiSummaryReady !== true) return t('insight.viewResultsAiPending')
  return undefined
}

function onViewResults(row: InsightProductRow) {
  const tid = row.taskId?.trim()
  if (!tid) {
    ElMessage.warning(t('insight.viewResultsNoTask'))
    return
  }
  const q: Record<string, string> = {
    title: row.title,
    asin: row.asin,
    country: row.countryLabel,
    price: row.priceLabel,
    rating: row.rating > 0 ? String(row.rating) : '',
    reviews: String(row.reviewCount),
    model: row.aiModel,
    analyzedAt: row.createdAt,
  }
  if (row.imageUrl && isLikelyHttpImageUrl(row.imageUrl)) {
    q.imageUrl = row.imageUrl
  }
  void router.push({
    path: `/insight-analysis/result/${encodeURIComponent(tid)}`,
    query: q,
  })
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
  justify-content: flex-end;
  gap: 12px;
  margin-bottom: 16px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

/* Element Plus 相邻按钮默认有 margin-left（约 12px），会盖掉 flex gap；清零后 gap 才生效 */
.toolbar-right :deep(.el-button) {
  margin-inline: 0;
}

/* 仅图标的刷新：与默认按钮同高的正方形外框 */
.toolbar-refresh-square {
  width: var(--el-component-size);
  min-width: var(--el-component-size);
  height: var(--el-component-size);
  padding: 0;
}

.upload-reviews-intro {
  margin: 0 0 14px;
  font-size: 14px;
  line-height: 1.55;
  color: var(--el-text-color-regular);
}

.form-field-hint {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.45;
  color: var(--el-text-color-secondary);
}

.upload-template-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  margin-bottom: 20px;
  background: var(--el-color-primary-light-9);
  border: 1px solid var(--el-color-primary-light-5);
  border-radius: 6px;
}

.upload-template-strip-left {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.upload-template-strip-icon {
  flex-shrink: 0;
  font-size: 18px;
  color: var(--el-color-primary);
}

.upload-template-strip-text {
  font-size: 14px;
  color: var(--el-text-color-primary);
  line-height: 1.4;
}

.upload-template-download-btn {
  flex-shrink: 0;
  font-weight: 500;
}

.upload-reviews-form {
  margin-top: 4px;
}

.upload-file-section-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin-bottom: 10px;
}

.upload-file-zone {
  border: 1px dashed var(--el-border-color);
  border-radius: 6px;
  padding: 8px 14px;
  background: var(--el-fill-color-blank);
  transition:
    border-color 0.28s ease,
    box-shadow 0.28s ease,
    background-color 0.28s ease;
}

.upload-file-zone:hover,
.upload-file-zone:focus-within {
  border-color: var(--el-color-primary-light-3);
  box-shadow: 0 0 0 1px var(--el-color-primary-light-7);
  background-color: var(--el-color-primary-light-9);
}

.upload-file-inner :deep(.el-upload) {
  display: block;
  width: auto;
}

.upload-file-trigger-row {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  flex-wrap: wrap;
  gap: 10px;
  cursor: pointer;
  min-height: 22px;
}

.upload-file-status {
  font-size: 14px;
  color: var(--el-text-color-primary);
  word-break: break-all;
}

.upload-file-zone .upload-file-status--placeholder {
  color: var(--el-color-primary);
}

.upload-file-hint {
  margin: 10px 0 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--el-text-color-secondary);
}

.upload-reviews-footer {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.insight-table {
  width: 100%;
}

.insight-model-cell {
  display: inline-block;
  max-width: 118px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: bottom;
}

/* 下载 / 查看 / 删除：与词典审核「通过」同款实心 small 按钮 */
.insight-actions-row {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
  width: 100%;
  max-width: 100%;
}

.insight-actions-row :deep(.el-button) {
  margin-left: 0 !important;
  margin-right: 0 !important;
  flex-shrink: 0;
}

.thumb {
  width: 48px;
  height: 48px;
  border-radius: 6px;
  display: block;
  background: var(--el-fill-color-light);
  box-sizing: border-box;
}

.thumb :deep(.el-image__inner) {
  object-position: center;
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
