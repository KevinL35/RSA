<template>
  <el-card class="view-card" v-loading="loading">
    <header class="page-header">
      <h2 class="page-title">{{ t('insight.title') }}</h2>
      <p class="page-subtitle">{{ t('insight.pageSubtitle') }}</p>
    </header>
    <div class="toolbar">
      <div class="toolbar-left">
        <el-button type="primary" @click="onAddProduct">{{ t('insight.addProduct') }}</el-button>
        <el-button
          type="primary"
          :disabled="!canMutateInsightTasks"
          @click="onUploadReviews"
        >
          {{ t('insight.uploadReviews') }}
        </el-button>
      </div>
      <el-button
        class="toolbar-refresh-square"
        :icon="Refresh"
        @click="onRefresh"
        :loading="loading"
        :title="t('insight.refresh')"
      />
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
      <el-table-column :label="t('insight.colInsightModel')" width="132">
        <template #default="{ row }">
          <el-tooltip :content="row.aiModel" placement="top" :show-after="400">
            <span class="insight-model-cell">{{ row.aiModelList }}</span>
          </el-tooltip>
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
              link
              :disabled="downloadReviewsDisabled(row)"
              :loading="downloadReviewingId === row.taskId"
              @click="onDownloadReviews(row)"
            >
              {{ t('insight.downloadReviews') }}
            </el-button>
            <el-button
              type="primary"
              link
              :disabled="viewResultsDisabled(row)"
              :title="viewResultsDisabled(row) ? t('insight.viewResultsDisabledHint') : undefined"
              @click="onViewResults(row)"
            >
              {{ t('insight.viewResults') }}
            </el-button>
            <el-button
              type="danger"
              link
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
        <el-form-item :label="t('insight.formDictionaryVertical')" required>
          <el-select
            v-model="dictionaryVerticalId"
            class="insight-model-select"
            :teleported="false"
          >
            <el-option
              v-for="opt in dictionaryVerticalOptions"
              :key="opt.id"
              :label="opt.label"
              :value="opt.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('insight.formInsightModel')" required>
          <el-select
            v-model="insightModelId"
            class="insight-model-select"
            clearable
            :teleported="false"
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
            :fallback-placements="['bottom-start', 'bottom', 'bottom-end']"
            :popper-options="uploadInsightSelectPopperOptions"
          >
            <el-option
              v-for="opt in dictionaryVerticalOptions"
              :key="opt.id"
              :label="opt.label"
              :value="opt.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('insight.formInsightModel')" required>
          <el-select
            v-model="uploadInsightModelId"
            class="insight-model-select"
            clearable
            placement="bottom-start"
            :fallback-placements="['bottom-start', 'bottom', 'bottom-end']"
            :popper-options="uploadInsightSelectPopperOptions"
          >
            <el-option
              v-for="opt in insightModelOptions"
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
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { genFileId } from 'element-plus'
import type { UploadFile, UploadInstance, UploadRawFile } from 'element-plus'
import { DocumentCopy, Download, Plus, Refresh } from '@element-plus/icons-vue'
import type { ApiConfigRow } from '../../settings/apiConfig.shared'
import { insightApiConfigRows } from '../../settings/apiConfig.shared'
import { deleteInsightTask, fetchInsightTasks } from '../../tasks/api'
import type { InsightTaskRow } from '../../tasks/types'
import {
  extractAsinFromAmazonUrl,
  isLikelyAmazonAsin,
  looksLikeAmazonProductUrl,
  resolveProductIdForUploadReviews,
} from '../../../shared/utils/amazonAsin'
import {
  formatInsightModelLine,
  formatInsightModelLineByProviderId,
  formatInsightModelShort,
} from '../../../shared/utils/insightModelLabel'
import { downloadReviewImportTemplate, downloadReviewsExcel } from '../../../shared/utils/excelDownload'
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

const { t, locale } = useI18n()
const router = useRouter()
const auth = useAuthStore()
const canMutateInsightTasks = computed(() => auth.canRetryInsightTasks.value)

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
  /** 完整「名称：模型」，用于结果页与 tooltip */
  aiModel: string
  /** 列表紧凑展示（多为模型 id） */
  aiModelList: string
  reviewStatus: 'fetching' | 'completed' | 'failed'
  reviewStatusLabel: string
  statusLabel: string
  /** insight_tasks.status，用于操作按钮禁用逻辑 */
  taskStatus?: string
  /**
   * 列表缩略图重试阶段：extra 图 → 主 CDN → 备用 CDN → 占位。
   * Amazon 对无效 ASIN 常返回 200 + 1×1 GIF，需配合 @load 尺寸判断。
   */
  imageThumbPhase?: 'extra' | 'amazon_primary' | 'amazon_fallback' | 'exhausted'
  /** 真实洞察任务 UUID；缺省则结果页使用 demo 数据 */
  taskId?: string
  dictionaryVerticalLabel: string
}

const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const pageSizeOptions = [10, 20, 50] as const

const dictionaryVerticals = ref<DictionaryVerticalItem[]>([])
const dictionaryVerticalId = ref('general')
const uploadDictionaryVerticalId = ref('general')

const addDialogVisible = ref(false)
const linkInputs = ref<string[]>([''])
const insightModelId = ref<string>('ins_builtin')
const dialogSubmitting = ref(false)
const uploadDialogVisible = ref(false)
const uploadLinkInput = ref('')
const uploadInsightModelId = ref('ins_builtin')
const uploadExcelFile = ref<File | null>(null)
const uploadExcelRef = ref<UploadInstance | null>(null)
const uploadSubmitting = ref(false)
/** 与后端 import-reviews 一致 */
const UPLOAD_REVIEW_MAX_BYTES = 10 * 1024 * 1024
/** 上传弹窗内下拉固定向下展开（避免在 dialog 内被 flip 到上方） */
const uploadInsightSelectPopperOptions = {
  modifiers: [{ name: 'flip', enabled: false }],
}
const downloadReviewingId = ref<string | null>(null)
const deletingTaskId = ref<string | null>(null)

const REVIEW_EXPORT_COLUMNS = [
  { label: '平台', key: 'platform' },
  { label: 'ASIN', key: 'product_id' },
  { label: '发布时间', key: 'reviewed_at' },
  { label: '标题', key: 'title' },
  { label: '评论', key: 'raw_text' },
] as const

const insightModelOptions = computed(() =>
  insightApiConfigRows.value.map((row) => ({
    id: row.id,
    label: formatInsightModelLine(row, t),
  })),
)

const dictionaryVerticalOptions = computed(() => {
  if (dictionaryVerticals.value.length > 0) {
    return dictionaryVerticals.value.map((v) => ({
      id: v.id,
      label: locale.value === 'zh-CN' ? v.label_zh : v.label_en,
    }))
  }
  return [
    { id: 'general', label: locale.value === 'zh-CN' ? '默认词典' : 'Default dictionary' },
    { id: 'electronics', label: locale.value === 'zh-CN' ? '电子产品' : 'Electronics' },
  ]
})

function verticalLabelForTask(vid: string | null | undefined): string {
  const id = (vid || 'general').trim() || 'general'
  if (id === 'general') {
    return locale.value === 'zh-CN' ? '默认词典' : 'Default dictionary'
  }
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
  insightModelId.value = 'ins_builtin'
  dictionaryVerticalId.value = 'general'
}

function buildDefaultRows(zh: boolean): InsightProductRow[] {
  const demoLine = formatInsightModelLine(
    { name: t('insight.demoInsightProviderName'), model: 'deepseek-chat' },
    t,
  )
  const demoList = 'deepseek-chat'
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
      aiModel: demoLine,
      aiModelList: demoList,
      reviewStatus: 'completed',
      reviewStatusLabel: t('insight.reviewStatus.completed'),
      statusLabel: t('insight.flowStatus.done'),
      taskStatus: 'success',
      taskId: 'demo',
      imageThumbPhase: 'exhausted',
      dictionaryVerticalLabel: zh ? '电子产品' : 'Electronics',
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
      aiModel: demoLine,
      aiModelList: demoList,
      reviewStatus: 'completed',
      reviewStatusLabel: t('insight.reviewStatus.completed'),
      statusLabel: t('insight.flowStatus.done'),
      taskStatus: 'success',
      taskId: 'demo',
      imageThumbPhase: 'exhausted',
      dictionaryVerticalLabel: zh ? '默认词典' : 'Default dictionary',
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
      aiModel: demoLine,
      aiModelList: demoList,
      reviewStatus: 'fetching',
      reviewStatusLabel: t('insight.reviewStatus.fetching'),
      statusLabel: t('insight.flowStatus.analyzing'),
      taskStatus: 'running',
      taskId: 'demo',
      imageThumbPhase: 'exhausted',
      dictionaryVerticalLabel: zh ? '默认词典' : 'Default dictionary',
    },
  ]
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

/** 洞察状态展示：分析中 / 已完成 / 失败（合并 pending+running → 分析中） */
function flowInsightStatusLabel(status: string): string {
  const key = classifyInsightFlowStatus(status)
  return t(`insight.flowStatus.${key}`)
}

function classifyInsightFlowStatus(status: string): 'analyzing' | 'done' | 'failed' {
  if (status === 'success') return 'done'
  if (status === 'failed' || status === 'cancelled') return 'failed'
  return 'analyzing'
}

function displayProviderLabel(providerId: string | null) {
  return formatInsightModelLineByProviderId(providerId, insightApiConfigRows.value, t)
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
    aiModelList: formatInsightModelShort(task.analysis_provider_id, insightApiConfigRows.value, t),
    reviewStatus: rs,
    reviewStatusLabel: reviewStatusLabel(rs),
    statusLabel: flowInsightStatusLabel(task.status),
    taskStatus: task.status,
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

async function hydrateRowsWithReviewStats(taskRows: InsightTaskRow[]) {
  const byId = new Map<string, InsightProductRow>()
  for (const r of rows.value) {
    if (r.taskId) byId.set(r.taskId, r)
  }
  await Promise.all(
    taskRows.map(async (task) => {
      try {
        const res = await fetchInsightTaskReviews(task.id, 20000)
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
        row.statusLabel = flowInsightStatusLabel(task.status)
      } catch {
        // Ignore per-row hydration errors to keep list render resilient.
      }
    }),
  )
}

async function loadTasks() {
  loading.value = true
  await ensureDictionaryVerticals()
  try {
    const res = await fetchInsightTasks({ limit: 50 })
    const taskRows = res.items ?? []
    rows.value = taskRows.map(mapTaskToRow)
    await hydrateRowsWithReviewStats(taskRows)
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

function downloadReviewsDisabled(row: InsightProductRow): boolean {
  const tid = row.taskId
  return !tid || tid === 'demo' || row.reviewStatus !== 'completed'
}

function deleteInsightDisabled(row: InsightProductRow): boolean {
  const tid = row.taskId
  return !canMutateInsightTasks.value || !tid || tid === 'demo'
}

async function onDeleteInsight(row: InsightProductRow) {
  const tid = row.taskId
  if (!tid || tid === 'demo' || !canMutateInsightTasks.value) return
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
  if (!tid || tid === 'demo') {
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
        analysis_provider_id: id,
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
    await loadTasks()
    for (const taskId of createdTaskIds) {
      void (async () => {
        try {
          await postInsightTaskFetchReviews(taskId)
          await loadTasks()
          await postInsightTaskAnalyze(taskId)
          await loadTasks()
        } catch (err) {
          const msg = err instanceof Error ? err.message : String(err)
          ElMessage.warning(`${t('insight.addProductPipelineFailed')}: ${msg}`)
          await loadTasks()
        }
      })()
    }
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
  uploadInsightModelId.value = 'ins_builtin'
  uploadDictionaryVerticalId.value = 'general'
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
  const id = uploadInsightModelId.value
  if (!id) {
    ElMessage.warning(t('insight.addProductNeedModel'))
    return
  }
  const cfg = insightApiConfigRows.value.find((r) => r.id === id)
  if (!cfg) {
    ElMessage.warning(t('insight.insightModelMissing'))
    return
  }
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
      analysis_provider_id: id,
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
  return s === 'pending' || s === 'running'
}

function onViewResults(row: InsightProductRow) {
  const tid = row.taskId ?? 'demo'
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
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

/* Element Plus 相邻按钮默认有 margin-left（约 12px），会盖掉 flex gap；清零后 gap 才生效 */
.toolbar-left :deep(.el-button) {
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

/* 下载 / 查看 / 删除：从左起排，不靠表格右缘 */
.insight-actions-row {
  display: flex;
  flex-direction: row;
  flex-wrap: nowrap;
  align-items: center;
  justify-content: flex-start;
  column-gap: 2px;
  width: 100%;
  max-width: 100%;
}

.insight-actions-row :deep(.el-button) {
  margin-left: 0 !important;
  margin-right: 0 !important;
  padding-left: 6px;
  padding-right: 6px;
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
