<template>
  <div class="result-page" v-loading="loading">
    <el-alert
      v-if="errorMsg"
      type="error"
      :closable="false"
      show-icon
      class="err-banner"
      :title="errorMsg"
    />
    <el-alert
      v-if="emptyState"
      type="warning"
      :closable="false"
      show-icon
      class="err-banner"
      :title="emptyState.message"
      :description="emptyState.hint"
    />

    <section class="result-header-card">
      <div class="result-header-inner">
        <div v-if="headerProductImageUrl" class="result-header-thumb">
          <el-image
            :src="headerProductImageUrl"
            fit="contain"
            referrerpolicy="no-referrer"
            class="result-header-thumb-img"
          >
            <template #error>
              <div class="result-header-thumb-fallback" />
            </template>
          </el-image>
        </div>
        <div class="result-header-body">
          <div class="result-header-title-row">
            <h1 class="result-main-title">{{ mainAsinTitle }}</h1>
            <div class="result-header-actions">
              <button
                v-if="canReanalyzeInsight"
                type="button"
                class="rsa-text-back-btn"
                :disabled="loading || reanalyzeSubmitting || aiSummarySubmitting"
                @click="onReanalyzeInsight"
              >
                {{ reanalyzeSubmitting ? t('insightResult.reanalyzing') : t('insightResult.reanalyze') }}
              </button>
              <button type="button" class="rsa-text-back-btn" @click="goBack">
                {{ t('insightResult.back') }}
              </button>
            </div>
          </div>
          <p class="result-meta-line">{{ metaSubtitle }}</p>
        </div>
      </div>
    </section>

    <section class="dim-grid">
      <div
        v-for="dim in dimensionOrder"
        :key="dim"
        class="dim-card"
        role="button"
        tabindex="0"
        @click="openCardExpand(dim)"
        @keydown.enter.prevent="openCardExpand(dim)"
        @keydown.space.prevent="openCardExpand(dim)"
      >
        <div class="dim-card-head">
          <span class="dim-tag" :class="`dim-tag--${dim}`">{{ dimTitle(dim) }}</span>
          <div class="dim-card-head-right dim-metrics-cols">
            <span class="dim-metric-label dim-metric-cell dim-metric-cell--count">{{
              t('insightResult.cardReviewCount')
            }}</span>
            <span class="dim-metric-label dim-metric-cell dim-metric-cell--share">{{
              t('insightResult.cardShare')
            }}</span>
          </div>
        </div>
        <div class="dim-card-body">
          <template v-if="cardRows(dim).length">
            <div v-for="(row, idx) in cardRows(dim)" :key="idx" class="dim-row">
              <span class="dim-row-label" :title="row.label">{{ row.label }}</span>
              <span class="dim-row-num dim-metric-cell dim-metric-cell--count">{{ row.count }}</span>
              <span class="dim-row-num dim-metric-cell dim-metric-cell--share">{{ row.pct }}%</span>
            </div>
          </template>
          <div v-else class="dim-empty">{{ t('insightResult.cardEmpty') }}</div>
        </div>
      </div>
    </section>

    <section v-if="dashboard && !emptyState" class="panel ai-insight-panel" v-loading="aiSummarySubmitting">
      <div class="ai-insight-head">
        <h3 class="subpanel-title">{{ t('insightResult.aiSectionTitle') }}</h3>
        <button
          v-if="canReanalyzeInsight"
          type="button"
          class="rsa-text-back-btn"
          :disabled="loading || aiSummarySubmitting || reanalyzeSubmitting"
          @click="onGenerateAiSummary"
        >
          {{ aiSummarySubmitting ? t('insightResult.aiRegenerating') : t('insightResult.aiRegenerate') }}
        </button>
      </div>
      <div v-if="storedAiSummaryText" class="ai-insight-body">{{ storedAiSummaryText }}</div>
      <ul v-else-if="aiSummaryLines.length" class="ai-insight-list">
        <li v-for="(line, i) in aiSummaryLines" :key="i">{{ line }}</li>
      </ul>
      <div v-else class="dim-empty ai-insight-empty">{{ t('insightResult.aiSectionEmpty') }}</div>
    </section>

    <section class="split-row wordcloud-rank-row">
      <div class="panel half wordcloud-panel">
        <div class="wordcloud-panel-head">
          <h3 class="subpanel-title">{{ t('insightResult.wordCloudTitle') }}</h3>
          <el-select
            v-model="wordCloudDimension"
            class="wordcloud-dim-select"
            filterable
            placement="bottom-start"
            :fallback-placements="selectFallbackPlacementsBottom"
            :popper-options="selectPopperOptionsNoFlip"
          >
            <el-option :label="t('insightResult.wordCloudDimAll')" value="all" />
            <el-option v-for="d in dimensionOrder" :key="d" :label="dimTitle(d)" :value="d" />
          </el-select>
        </div>
        <div class="wordcloud-body">
          <WordCloudChart v-if="wordCloudItems.length > 0" :items="wordCloudItems" />
          <div v-else class="wordcloud-empty">{{ t('insightResult.wordCloudEmpty') }}</div>
        </div>
      </div>
      <div class="panel half rank-panel">
        <h2 class="panel-title">{{ t('insightResult.rankTitle') }}</h2>
        <el-table :data="rankingTableRows" stripe class="rank-table" max-height="320">
          <el-table-column prop="dimensionLabel" :label="t('insightResult.colDimension')" width="120" />
          <el-table-column prop="keyword" :label="t('insightResult.colKeyword')" min-width="160" show-overflow-tooltip />
          <el-table-column prop="freq" :label="t('insightResult.colFreq')" width="88" />
          <el-table-column prop="trend" :label="t('insightResult.colTrend')" width="72" align="center" />
        </el-table>
      </div>
    </section>

    <section class="split-row evidence-row">
      <div class="panel pain-panel">
        <div class="pain-panel-head">
          <h3 class="subpanel-title">{{ t('insightResult.dimensionListTitle') }}</h3>
          <el-select
            v-model="painListDimension"
            class="pain-list-dim-select"
            filterable
            placement="bottom-start"
            :fallback-placements="selectFallbackPlacementsBottom"
            :popper-options="selectPopperOptionsNoFlip"
          >
            <el-option v-for="d in dimensionOrder" :key="d" :label="dimTitle(d)" :value="d" />
          </el-select>
        </div>
        <div v-if="dimensionListRows.length === 0" class="dim-empty pain-list-empty">
          {{ t('insightResult.wordCloudEmpty') }}
        </div>
        <ul v-else class="pain-list">
          <li
            v-for="r in dimensionListRows"
            :key="r.keyword"
            :class="{ active: selectedKeyword === r.keyword }"
            @click="selectedKeyword = r.keyword"
          >
            <span class="pain-dot">●</span>
            <span class="pain-kw">{{ r.keyword }}</span>
          </li>
        </ul>
      </div>
      <div class="panel evidence-panel">
        <h3 class="subpanel-title evidence-panel-title">{{ t('insightResult.evidenceTitle') }}</h3>
        <div class="evidence-list">
          <div v-if="!selectedKeyword" class="dim-empty evidence-hint">
            {{ t('insightResult.evidencePickKeyword') }}
          </div>
          <template v-else-if="paginatedEvidence.length">
            <div v-for="ev in paginatedEvidence" :key="String(ev.id)" class="evidence-block">
              <div class="evidence-block-head">
                <span class="evidence-time">{{ formatReviewDateTime(ev) }}</span>
                <button
                  v-if="evidenceHasQuoteText(ev)"
                  type="button"
                  class="evidence-toggle"
                  @click="toggleEvidenceExpand(ev)"
                >
                  {{
                    isEvidenceExpanded(ev)
                      ? t('insightResult.evidenceCollapse')
                      : t('insightResult.evidenceExpand')
                  }}
                </button>
              </div>
              <div class="evidence-quote-wrap">
                <div class="evidence-quote" :class="evidenceQuoteClass(ev)" v-html="highlightEvidence(ev)" />
              </div>
            </div>
          </template>
          <div v-else class="dim-empty">{{ t('insightResult.evidenceEmpty') }}</div>
        </div>
        <div v-if="selectedKeyword && evidenceTotalPages > 1" class="evidence-pager">
          <button
            type="button"
            class="rsa-text-back-btn"
            :disabled="evidencePage <= 1"
            @click="evidencePage--"
          >
            {{ t('insightResult.prev') }}
          </button>
          <span class="pager-text">
            {{ t('insightResult.pageOf', { n: evidencePage, m: evidenceTotalPages }) }}
          </span>
          <button
            type="button"
            class="rsa-text-back-btn"
            :disabled="evidencePage >= evidenceTotalPages"
            @click="evidencePage++"
          >
            {{ t('insightResult.next') }}
          </button>
        </div>
      </div>
    </section>

    <section class="panel trend-panel">
      <h3 class="subpanel-title">{{ t('insightResult.reviewTrendTitle') }}</h3>
      <div v-if="reviewTrendPoints.length > 0" class="trend-chart-wrap">
        <ReviewTrendChart :points="reviewTrendPoints" />
      </div>
      <div v-else class="trend-empty dim-empty">{{ t('insightResult.reviewTrendEmpty') }}</div>
    </section>

    <el-dialog v-model="expandVisible" :title="expandTitle" width="640px" destroy-on-close>
      <el-table :data="expandRows" stripe max-height="420">
        <el-table-column prop="label" :label="t('insightResult.colKeyword')" min-width="200" show-overflow-tooltip />
        <el-table-column prop="count" :label="t('insightResult.cardReviewCount')" width="100" />
        <el-table-column prop="pct" :label="t('insightResult.cardShare')" width="88">
          <template #default="{ row }">{{ row.pct }}%</template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import ReviewTrendChart from '../components/ReviewTrendChart.vue'
import WordCloudChart from '../components/WordCloudChart.vue'
import {
  SELECT_FALLBACK_PLACEMENTS_BOTTOM,
  selectPopperOptionsNoFlip,
} from '../../../shared/ui/elementSelectPlacement'
import { fetchInsightDashboard, postInsightAiSummary, postInsightTaskAnalyze } from '../api'
import { useAuthStore } from '../../auth/store/auth.store'
import { fetchTaxonomyPreview, type TaxonomyPreviewResponse } from '../../dictionary/api'
import type {
  Dimension6Key,
  InsightDashboardResponse,
  InsightEvidenceItem,
  PainRankItem,
  ReviewTimeseriesPoint,
} from '../dashboardTypes'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const canReanalyzeInsight = computed(() => auth.canRetryInsightTasks.value)
const reanalyzeSubmitting = ref(false)

const selectFallbackPlacementsBottom = SELECT_FALLBACK_PLACEMENTS_BOTTOM

const dimensionOrder: Dimension6Key[] = [
  'pros',
  'cons',
  'return_reasons',
  'purchase_motivation',
  'user_expectation',
  'usage_scenario',
]

/** 痛点排行榜仅统计「缺点」「退货原因」两维 */
const painRankingDimensions: Dimension6Key[] = ['cons', 'return_reasons']

/**
 * 词云色阶（与 dim-tag 同色相、略深，白底可读）
 * 六维语义：绿=优点、琥珀=缺点、玫红=退货、蓝=购买动机、青=期望、紫=场景
 */
const WORDCLOUD_PALETTES: Record<Dimension6Key, string[]> = {
  pros: ['#047857', '#059669', '#10b981', '#34d399', '#6ee7b7'],
  cons: ['#b45309', '#d97706', '#f59e0b', '#fbbf24', '#fcd34d'],
  return_reasons: ['#be123c', '#e11d48', '#f43f5e', '#fb7185', '#fda4af'],
  purchase_motivation: ['#1d4ed8', '#2563eb', '#3b82f6', '#60a5fa', '#93c5fd'],
  user_expectation: ['#0e7490', '#0891b2', '#06b6d4', '#22d3ee', '#67e8f9'],
  usage_scenario: ['#6d28d9', '#7c3aed', '#8b5cf6', '#a78bfa', '#c4b5fd'],
}

function hashKeywordHue(keyword: string): number {
  let h = 0
  for (let i = 0; i < keyword.length; i++) h = (h * 31 + keyword.charCodeAt(i)) >>> 0
  return h
}

/** 同一维度内用关键词哈希取色阶，避免整朵词云单色 */
function pickWordCloudColor(keyword: string, dim: Dimension6Key): string {
  const palette = WORDCLOUD_PALETTES[dim]
  if (!palette?.length) return '#047857'
  return palette[hashKeywordHue(keyword) % palette.length]!
}

/** 从 pain_ranking 行解析「主维度」（与 dimensionOrder 优先级一致） */
function primaryDimensionFromRankDims(dims: string[]): Dimension6Key {
  for (const d of dimensionOrder) {
    if (dims.includes(d)) return d
  }
  const first = dims[0]
  if (first && dimensionOrder.includes(first as Dimension6Key)) return first as Dimension6Key
  return 'pros'
}

function primaryDimensionForPainKeyword(keyword: string): Dimension6Key {
  const dash = dashboard.value
  if (!dash?.pain_ranking?.length) return 'pros'
  const low = keyword.trim().toLowerCase()
  const row = dash.pain_ranking.find((p) => p.keyword.trim().toLowerCase() === low)
  if (!row?.dimensions?.length) return 'pros'
  return primaryDimensionFromRankDims(row.dimensions)
}

const loading = ref(false)
const errorMsg = ref('')
const dashboard = ref<InsightDashboardResponse | null>(null)
/** 当前任务词典垂直下的 taxonomy，用于证据句同义词高亮 */
const taxonomyPreview = ref<TaxonomyPreviewResponse | null>(null)

const taskId = computed(() => String(route.params.taskId || ''))

type WordCloudDimFilter = 'all' | Dimension6Key

const wordCloudDimension = ref<WordCloudDimFilter>('all')
const painListDimension = ref<Dimension6Key>('pros')
const selectedKeyword = ref<string | null>(null)
const aiSummarySubmitting = ref(false)

const expandVisible = ref(false)
const expandDim = ref<Dimension6Key | null>(null)


const emptyState = computed(() => dashboard.value?.empty_state ?? null)

/** 基于看板数据的规则归纳（非大模型），供「AI 智能分析」快速阅读 */
const aiSummaryLines = computed(() => {
  const d = dashboard.value
  if (!d || d.empty_state) return []
  const lines: string[] = []
  const total = d.review_total_count
  const matched = d.matched_review_count
  if (typeof total === 'number' && Number.isFinite(total) && typeof matched === 'number' && Number.isFinite(matched)) {
    lines.push(t('insightResult.aiLineCoverage', { total, matched }))
  }
  const ranked = [...(d.pain_ranking ?? [])].sort((a, b) => b.count - a.count).slice(0, 5)
  for (const p of ranked) {
    const dims = (p.dimensions ?? [])
      .filter((x): x is Dimension6Key => dimensionOrder.includes(x as Dimension6Key))
      .map((x) => dimTitle(x))
    const dimStr = dims.length ? dims.join(t('insightResult.aiDimJoiner')) : '—'
    lines.push(t('insightResult.aiLineKeyword', { kw: p.keyword, n: p.count, dims: dimStr }))
  }
  const dc = d.dimension_counts
  if (dc && typeof dc === 'object') {
    let bestDim: Dimension6Key | null = null
    let bestN = 0
    const dimMap = dc as Partial<Record<Dimension6Key, number>>
    for (const k of dimensionOrder) {
      const n = dimMap[k]
      if (typeof n === 'number' && n > bestN) {
        bestN = n
        bestDim = k
      }
    }
    if (bestDim && bestN > 0) {
      lines.push(t('insightResult.aiLineStrongDim', { dim: dimTitle(bestDim), n: bestN }))
    }
  }
  return lines
})

const storedAiSummaryText = computed(() => (dashboard.value?.ai_summary?.text || '').trim())

function formatLocalDateTime(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso.replace('T', ' ').slice(0, 19)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

/** 主标题：商品 ID（如 ASIN） */
const mainAsinTitle = computed(() => {
  const d = dashboard.value
  if (d?.product_id) return d.product_id
  const a = (route.query.asin as string | undefined)?.trim()
  return a || t('insightResult.productFallback')
})

/** 副标题仅展示短模型名：内置源统一 rsa-v1，其它为 analysis_provider_id（不用列表页「平台自研：…」长文案） */
const insightModelDisplay = computed(() => {
  const id = dashboard.value?.analysis_provider_id
  if (id && String(id).trim() !== '' && id !== 'ins_builtin') return String(id).trim()
  return 'rsa-v1'
})

const analyzedAtFormatted = computed(() => {
  const iso = dashboard.value?.analyzed_at
  if (iso) return formatLocalDateTime(iso)
  const q = (route.query.analyzedAt as string | undefined)?.trim()
  if (q) return q
  return formatLocalDateTime(new Date().toISOString())
})

function isHeaderImageUrl(s: string): boolean {
  const x = s.trim().toLowerCase()
  return x.startsWith('https://') || x.startsWith('http://') || x.startsWith('data:image/')
}

/** 主图：优先接口 product_snapshot，其次列表跳转带来的 query.imageUrl */
const headerProductImageUrl = computed(() => {
  const snap = dashboard.value?.product_snapshot
  const fromApi = typeof snap?.image_url === 'string' ? snap.image_url.trim() : ''
  if (fromApi && isHeaderImageUrl(fromApi)) return fromApi
  const q = (route.query.imageUrl as string | undefined)?.trim()
  if (q && isHeaderImageUrl(q)) return q
  return ''
})

const headerReviewTotal = computed(() => {
  const n = dashboard.value?.review_total_count
  return typeof n === 'number' && Number.isFinite(n) ? n : null
})

const headerMatchedReviews = computed(() => {
  const n = dashboard.value?.matched_review_count
  return typeof n === 'number' && Number.isFinite(n) ? n : null
})

const metaSubtitle = computed(() =>
  t('insightResult.headerMetaLine', {
    model: insightModelDisplay.value,
    time: analyzedAtFormatted.value,
    total: headerReviewTotal.value ?? '—',
    matched: headerMatchedReviews.value ?? '—',
  }),
)

const reviewTrendPoints = computed((): ReviewTimeseriesPoint[] => dashboard.value?.review_timeseries ?? [])

function dimTitle(dim: Dimension6Key) {
  return t(`insightResult.dim.${dim}`)
}

function goBack() {
  router.push('/insight-analysis')
}

async function onGenerateAiSummary() {
  if (!canReanalyzeInsight.value || !taskId.value) return
  aiSummarySubmitting.value = true
  try {
    const reg = !!storedAiSummaryText.value
    const res = await postInsightAiSummary(taskId.value, { regenerate: reg })
    const next = res.ai_summary
    if (next && dashboard.value) {
      dashboard.value = { ...dashboard.value, ai_summary: next }
    }
    ElMessage.success(reg ? t('insightResult.aiRegenerateOk') : t('insightResult.aiGenerateOk'))
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    ElMessage.error(`${t('insightResult.aiGenerateFail')}: ${msg}`)
  } finally {
    aiSummarySubmitting.value = false
  }
}

async function onReanalyzeInsight() {
  if (!canReanalyzeInsight.value || !taskId.value) return
  try {
    await ElMessageBox.confirm(
      t('insightResult.reanalyzeConfirm'),
      t('insightResult.reanalyzeTitle'),
      {
        type: 'warning',
        confirmButtonText: t('insight.dialogConfirm'),
        cancelButtonText: t('insight.dialogCancel'),
      },
    )
  } catch {
    return
  }
  reanalyzeSubmitting.value = true
  errorMsg.value = ''
  try {
    await postInsightTaskAnalyze(taskId.value, { forceReanalyze: true })
    ElMessage.success(t('insightResult.reanalyzeOk'))
    await load()
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    ElMessage.error(`${t('insightResult.reanalyzeFail')}: ${msg}`)
  } finally {
    reanalyzeSubmitting.value = false
  }
}

function painForDimension(dim: Dimension6Key, list: PainRankItem[]) {
  return list.filter((p) => p.dimensions.includes(dim))
}

function cardRows(dim: Dimension6Key): { label: string; count: number; pct: number }[] {
  const dash = dashboard.value
  if (!dash) return []
  const items = painForDimension(dim, dash.pain_ranking)
  /** 占比分母：全量 pain_ranking 频次之和（整体），非单维度内合计 */
  const globalTotal = dash.pain_ranking.reduce((s, p) => s + p.count, 0) || 1
  return items.map((x) => ({
    label: x.keyword,
    count: x.count,
    pct: Math.round((x.count / globalTotal) * 100),
  }))
}

function primaryPainRankingDimension(dims: string[]): Dimension6Key {
  for (const d of painRankingDimensions) {
    if (dims.includes(d)) return d
  }
  return 'cons'
}

function trendForKeyword(kw: string) {
  let h = 0
  for (let i = 0; i < kw.length; i++) h = (h + kw.charCodeAt(i) * (i + 1)) % 3
  return h === 0 ? '↑' : h === 1 ? '→' : '↓'
}

/** 某维度下关键词频次聚合（词云与维度列表共用） */
function keywordsAggregatedForDimension(dim: Dimension6Key): { keyword: string; count: number }[] {
  const dash = dashboard.value
  if (!dash?.pain_ranking?.length) return []
  const map = new Map<string, number>()
  for (const p of dash.pain_ranking) {
    if (!p.dimensions.includes(dim)) continue
    const k = p.keyword.trim()
    if (!k) continue
    map.set(k, (map.get(k) || 0) + p.count)
  }
  return [...map.entries()]
    .map(([keyword, count]) => ({ keyword, count }))
    .sort((a, b) => b.count - a.count)
}

/** 词云「全部」：使用排行榜全量关键词（与后端 pain_ranking 一致，不按维度过滤） */
function keywordsAggregatedAllDimensions(): { keyword: string; count: number }[] {
  const dash = dashboard.value
  if (!dash?.pain_ranking?.length) return []
  return dash.pain_ranking
    .map((p) => ({ keyword: p.keyword.trim(), count: p.count }))
    .filter((x) => x.keyword)
    .sort((a, b) => b.count - a.count)
}

const rankingTableRows = computed(() => {
  const dash = dashboard.value
  if (!dash) return []
  const list = dash.pain_ranking
    .filter((p) => p.dimensions.some((d) => painRankingDimensions.includes(d as Dimension6Key)))
    .sort((a, b) => b.count - a.count)
  return list.map((p) => {
    const dim = primaryPainRankingDimension(p.dimensions)
    return {
      dimensionLabel: dimTitle(dim),
      keyword: p.keyword,
      freq: p.count,
      trend: trendForKeyword(p.keyword),
    }
  })
})

const wordCloudItems = computed(() => {
  const mode = wordCloudDimension.value
  const rows =
    mode === 'all' ? keywordsAggregatedAllDimensions() : keywordsAggregatedForDimension(mode)
  return rows.slice(0, 80).map(({ keyword, count }) => {
    const dimForColor = mode === 'all' ? primaryDimensionForPainKeyword(keyword) : mode
    return {
      name: keyword,
      value: count,
      color: pickWordCloudColor(keyword, dimForColor),
      dimensionLabel: dimTitle(dimForColor),
    }
  })
})

const dimensionListRows = computed(() => keywordsAggregatedForDimension(painListDimension.value).slice(0, 48))

const filteredEvidence = computed(() => {
  const dash = dashboard.value
  if (!dash) return []
  const kw = selectedKeyword.value
  if (!kw) return []
  const lower = kw.trim().toLowerCase()
  const dim = painListDimension.value
  return dash.evidence.items.filter((ev) => {
    if (String(ev.dimension) !== dim) return false
    const kws = ev.keywords
    if (!Array.isArray(kws) || kws.length === 0) return false
    return kws.some((k) => String(k).trim().toLowerCase() === lower)
  })
})

const EVIDENCE_PAGE_SIZE = 5
const evidencePage = ref(1)

const evidenceTotalPages = computed(() =>
  Math.max(1, Math.ceil(filteredEvidence.value.length / EVIDENCE_PAGE_SIZE)),
)

const paginatedEvidence = computed(() => {
  const start = (evidencePage.value - 1) * EVIDENCE_PAGE_SIZE
  return filteredEvidence.value.slice(start, start + EVIDENCE_PAGE_SIZE)
})

/** 证据条「展开」状态：按 review_dimension_analysis.id 记忆，切换关键词/维度/翻页时清空 */
const evidenceExpandedIds = ref<Set<string>>(new Set())

watch(painListDimension, () => {
  selectedKeyword.value = null
})

/** 换关键词或维度时回到第 1 页并折叠所有证据 */
watch([selectedKeyword, painListDimension], () => {
  evidencePage.value = 1
  evidenceExpandedIds.value = new Set()
})

watch(evidencePage, () => {
  evidenceExpandedIds.value = new Set()
})

function evidenceDisplayPlainText(ev: InsightEvidenceItem): string {
  const rawFull = typeof ev.review?.raw_text === 'string' ? ev.review.raw_text : ''
  const quote = typeof ev.evidence_quote === 'string' ? ev.evidence_quote : ''
  return (rawFull.trim() || quote.trim()) || ''
}

function evidenceHasQuoteText(ev: InsightEvidenceItem): boolean {
  return evidenceDisplayPlainText(ev).length > 0
}

function isEvidenceExpanded(ev: InsightEvidenceItem): boolean {
  return evidenceExpandedIds.value.has(String(ev.id))
}

function toggleEvidenceExpand(ev: InsightEvidenceItem) {
  const k = String(ev.id)
  const next = new Set(evidenceExpandedIds.value)
  if (next.has(k)) next.delete(k)
  else next.add(k)
  evidenceExpandedIds.value = next
}

function evidenceQuoteClass(ev: InsightEvidenceItem) {
  if (!evidenceHasQuoteText(ev)) return {}
  return { 'evidence-quote--collapsed': !isEvidenceExpanded(ev) }
}

const expandRows = computed(() => (expandDim.value ? cardRows(expandDim.value) : []))
const expandTitle = computed(() => (expandDim.value ? dimTitle(expandDim.value) : ''))

function openCardExpand(dim: Dimension6Key) {
  expandDim.value = dim
  expandVisible.value = true
}

/** 证据条仅展示评论日期 YYYY-MM-DD（无则 —） */
function formatReviewDateTime(ev: InsightEvidenceItem): string {
  const raw = ev.review?.reviewed_at
  if (typeof raw !== 'string' || !raw.trim()) return '—'
  const s = raw.trim()
  const day = s.slice(0, 10)
  if (/^\d{4}-\d{2}-\d{2}$/.test(day)) return day
  const t = s.split('T')[0] ?? ''
  return /^\d{4}-\d{2}-\d{2}$/.test(t) ? t : '—'
}

function escapeHtml(s: string) {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

/** 当前维度下每条词典词条 = 一组同义词（规范词 + aliases） */
function buildSynonymGroups(dim: Dimension6Key, preview: TaxonomyPreviewResponse | null): string[][] {
  const block = preview?.dimensions?.[dim]
  const entries = block?.entries
  if (!entries?.length) return []
  const out: string[][] = []
  for (const e of entries) {
    const can = String(e.canonical ?? '').trim()
    const als = Array.isArray(e.aliases)
      ? e.aliases.map((a) => String(a).trim()).filter(Boolean)
      : []
    const g = [...new Set([can, ...als].filter(Boolean))]
    if (g.length) out.push(g)
  }
  return out
}

function expandKeywordWithSynonyms(kw: string, groups: string[][]): string[] {
  const t = kw.trim()
  if (!t) return []
  const low = t.toLowerCase()
  for (const g of groups) {
    if (g.some((x) => x.toLowerCase() === low)) return [...g]
  }
  return [t]
}

function collectEvidenceHighlightTerms(ev: InsightEvidenceItem, groups: string[][]): string[] {
  const acc = new Set<string>()
  for (const k of ev.keywords ?? []) {
    for (const x of expandKeywordWithSynonyms(String(k), groups)) {
      if (x.trim()) acc.add(x.trim())
    }
  }
  const picked = selectedKeyword.value?.trim()
  if (picked) {
    for (const x of expandKeywordWithSynonyms(picked, groups)) {
      if (x.trim()) acc.add(x.trim())
    }
  }
  return [...acc].sort((a, b) => b.length - a.length)
}

/** 在已 escape 的正文上合并区间再包 mark，避免多次 replace 嵌套或覆盖 */
function highlightByMergedIntervals(escapedText: string, terms: string[]): string {
  if (!terms.length) return escapedText
  const intervals: [number, number][] = []
  for (const term of terms) {
    const piece = term.trim()
    if (!piece) continue
    const esc = escapeHtml(piece)
    if (!esc) continue
    const pattern = `(${escapeRegExp(esc)})`
    let re: RegExp
    try {
      re = new RegExp(pattern, 'giu')
    } catch {
      re = new RegExp(pattern, 'gi')
    }
    re.lastIndex = 0
    let m: RegExpExecArray | null
    while ((m = re.exec(escapedText)) !== null) {
      if (m.index === re.lastIndex) re.lastIndex++
      intervals.push([m.index, m.index + m[0].length])
    }
  }
  if (!intervals.length) return escapedText
  intervals.sort((a, b) => a[0] - b[0] || b[1] - a[1])
  const merged: [number, number][] = []
  for (const iv of intervals) {
    const last = merged[merged.length - 1]
    if (!last || iv[0] >= last[1]) merged.push([iv[0], iv[1]])
    else last[1] = Math.max(last[1], iv[1])
  }
  let out = ''
  let cur = 0
  for (const [s, e] of merged) {
    out += escapedText.slice(cur, s) + '<mark>' + escapedText.slice(s, e) + '</mark>'
    cur = e
  }
  out += escapedText.slice(cur)
  return out
}

function highlightEvidence(ev: InsightEvidenceItem) {
  const rawFull = typeof ev.review?.raw_text === 'string' ? ev.review.raw_text : ''
  const quote = typeof ev.evidence_quote === 'string' ? ev.evidence_quote : ''
  const raw = (rawFull.trim() || quote.trim()) || ''
  if (!raw) return ''
  const escaped = escapeHtml(raw)
  const groups = buildSynonymGroups(painListDimension.value, taxonomyPreview.value)
  const terms = collectEvidenceHighlightTerms(ev, groups)
  return highlightByMergedIntervals(escaped, terms)
}

async function loadTaxonomyForDashboard(d: InsightDashboardResponse | null) {
  taxonomyPreview.value = null
  if (!d?.dictionary_vertical_id) return
  const vid = String(d.dictionary_vertical_id).trim() || 'general'
  try {
    taxonomyPreview.value = await fetchTaxonomyPreview(vid)
  } catch {
    taxonomyPreview.value = null
  }
}

/** 后端 analyze 成功后异步触发 AI 摘要；用最多 4 次轮询等它写回，避免用户手动刷新 */
const AI_SUMMARY_POLL_INTERVAL_MS = 5000
const AI_SUMMARY_POLL_MAX = 4
let aiSummaryPollTimer: number | null = null

function clearAiSummaryPolling() {
  if (aiSummaryPollTimer != null) {
    window.clearTimeout(aiSummaryPollTimer)
    aiSummaryPollTimer = null
  }
}

function scheduleAiSummaryPolling(remaining: number) {
  clearAiSummaryPolling()
  if (remaining <= 0) return
  if ((dashboard.value?.ai_summary?.text || '').trim()) return
  aiSummaryPollTimer = window.setTimeout(async () => {
    aiSummaryPollTimer = null
    if ((dashboard.value?.ai_summary?.text || '').trim()) return
    if (!taskId.value) return
    try {
      const next = await fetchInsightDashboard(taskId.value, { evidence_limit: 5000, evidence_offset: 0 })
      dashboard.value = next
    } catch {
      /** 静默：保留已有看板数据 */
    }
    if (!(dashboard.value?.ai_summary?.text || '').trim()) {
      scheduleAiSummaryPolling(remaining - 1)
    }
  }, AI_SUMMARY_POLL_INTERVAL_MS)
}

async function load() {
  errorMsg.value = ''
  loading.value = true
  clearAiSummaryPolling()
  try {
    /** evidence_limit 调大：保证前端按「维度+关键词」过滤后能与 pain_ranking.count 对齐，不再出现「卡片 249 / 证据 1」 */
    dashboard.value = await fetchInsightDashboard(taskId.value, { evidence_limit: 5000, evidence_offset: 0 })
    painListDimension.value = 'pros'
    selectedKeyword.value = null
    await loadTaxonomyForDashboard(dashboard.value)
    if (!(dashboard.value?.ai_summary?.text || '').trim()) {
      scheduleAiSummaryPolling(AI_SUMMARY_POLL_MAX)
    }
  } catch (e) {
    errorMsg.value = e instanceof Error ? e.message : String(e)
    dashboard.value = null
    taxonomyPreview.value = null
    painListDimension.value = 'pros'
    selectedKeyword.value = null
  } finally {
    loading.value = false
  }
}

watch(
  () => taskId.value,
  () => {
    void load()
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  clearAiSummaryPolling()
})
</script>

<style scoped>
.result-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 8px 4px 32px;
}

.err-banner {
  margin-bottom: 12px;
}

.result-header-card {
  background: #fff;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  padding: 14px 18px 16px;
  margin-bottom: 20px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.result-header-inner {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.result-header-thumb {
  flex-shrink: 0;
  width: 72px;
  height: 72px;
  border-radius: 8px;
  overflow: hidden;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color-lighter);
  box-sizing: border-box;
}

.result-header-thumb-img {
  width: 72px;
  height: 72px;
  display: block;
}

.result-header-thumb-fallback {
  width: 100%;
  height: 100%;
  min-height: 72px;
  background: linear-gradient(135deg, #e2e8f0 0%, #cbd5e1 100%);
}

.result-header-body {
  min-width: 0;
  flex: 1;
}

.result-header-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.result-header-actions {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}


.result-main-title {
  margin: 0;
  min-width: 0;
  flex: 1;
  font-size: 20px;
  font-weight: 600;
  line-height: 1.3;
  color: var(--el-text-color-primary);
}

.result-meta-line {
  margin: 0;
  font-size: 14px;
  line-height: 1.55;
  color: var(--el-text-color-secondary);
}

.trend-panel {
  margin-bottom: 16px;
}

.trend-chart-wrap {
  width: 100%;
  min-height: 240px;
}

.trend-empty {
  min-height: 160px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px dashed var(--el-border-color);
  border-radius: 8px;
  padding: 16px;
}

.dim-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-bottom: 20px;
}

@media (max-width: 1100px) {
  .dim-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .dim-grid {
    grid-template-columns: 1fr;
  }
}

.dim-card {
  background: #fff;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  cursor: pointer;
  outline: none;
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}

.dim-card:hover {
  border-color: var(--el-color-primary-light-5);
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.08);
}

.dim-card:focus-visible {
  border-color: var(--el-color-primary);
  box-shadow: 0 0 0 2px var(--el-color-primary-light-7);
}

.dim-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--el-border-color-extra-light);
}

.dim-card-head-right {
  flex-shrink: 0;
}

/** 与数据行后两列同宽，与 flex 右对齐组合后垂线与正文一致 */
.dim-metrics-cols {
  display: grid;
  grid-template-columns: 4.75rem 4.25rem;
  column-gap: 0;
  align-items: center;
}

.dim-metric-cell {
  margin: 0;
  padding: 4px 8px 4px 10px;
  text-align: right;
  font-variant-numeric: tabular-nums;
  box-sizing: border-box;
}

.dim-metric-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.3;
  white-space: nowrap;
}

.dim-tag {
  display: inline-block;
  font-size: 12px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 4px;
}

.dim-tag--pros {
  color: #047857;
  background: #ecfdf5;
}
.dim-tag--cons {
  color: #b45309;
  background: #fffbeb;
}
.dim-tag--return_reasons {
  color: #be123c;
  background: #fff1f2;
}
.dim-tag--purchase_motivation {
  color: #1d4ed8;
  background: #eff6ff;
}
.dim-tag--user_expectation {
  color: #0e7490;
  background: #ecfeff;
}
.dim-tag--usage_scenario {
  color: #6d28d9;
  background: #f5f3ff;
}

.dim-card-body {
  max-height: 220px;
  overflow-y: auto;
  padding: 8px 12px 10px;
}

.dim-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 4.75rem 4.25rem;
  column-gap: 0;
  align-items: center;
  font-size: 13px;
  padding: 8px 0;
  border-bottom: 1px solid #f1f5f9;
  box-sizing: border-box;
}

.dim-row:last-child {
  border-bottom: none;
}

.dim-row-label {
  min-width: 0;
  padding-right: 10px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dim-row-num {
  color: var(--el-text-color-regular);
}

.dim-empty {
  font-size: 13px;
  color: var(--el-text-color-placeholder);
  padding: 12px 0;
  text-align: center;
}

.panel {
  background: #fff;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  padding: 14px 16px 16px;
  margin-bottom: 16px;
}

.panel-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.rank-panel > .panel-title {
  margin-bottom: 12px;
}

.rank-table {
  width: 100%;
}

.split-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-bottom: 16px;
}

.wordcloud-rank-row {
  align-items: stretch;
}

.wordcloud-rank-row .rank-panel {
  min-width: 0;
}

.wordcloud-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.wordcloud-panel-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.wordcloud-panel-head .subpanel-title {
  margin: 0;
}

.wordcloud-dim-select {
  width: 108px;
  flex-shrink: 0;
}

.wordcloud-body {
  flex: 1;
  min-height: 260px;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.wordcloud-body :deep(.wordcloud-zoom-wrap) {
  flex: 1;
  min-height: 240px;
}

.wordcloud-body :deep(.wordcloud-host) {
  min-height: 220px;
}

.wordcloud-empty {
  flex: 1;
  min-height: 240px;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 16px;
  font-size: 13px;
  color: var(--el-text-color-placeholder);
  border: 1px dashed var(--el-border-color);
  border-radius: 8px;
}

@media (max-width: 900px) {
  .split-row {
    grid-template-columns: 1fr;
  }
}

.half {
  margin-bottom: 0;
  min-height: 140px;
}

.subpanel-title {
  margin: 0 0 10px;
  font-size: 14px;
  font-weight: 600;
}

.placeholder-box {
  min-height: 100px;
  border: 1px dashed var(--el-border-color);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  padding: 12px;
  text-align: center;
}

.evidence-row {
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.35fr);
  /** 两栏各取自身内容高度：证据面板贴合内容，维度列表用自身固定高度 */
  align-items: start;
}

@media (min-width: 1000px) {
  .evidence-row {
    grid-template-columns: minmax(220px, 0.42fr) minmax(0, 1fr);
  }
}

@media (max-width: 900px) {
  .evidence-row {
    grid-template-columns: 1fr;
  }
}

.evidence-row .pain-panel,
.evidence-row .evidence-panel {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.evidence-panel .evidence-panel-title {
  flex-shrink: 0;
}

.pain-panel-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
  flex-shrink: 0;
}

.pain-panel-head .subpanel-title {
  margin: 0;
}

.pain-list-dim-select {
  width: 108px;
  flex-shrink: 0;
}

.pain-list-empty {
  padding: 16px 8px;
  text-align: center;
}

.pain-list {
  list-style: none;
  margin: 0;
  padding: 0;
  /** 固定容纳约 15 条单行关键词；不足 15 条时仍按真实条数显示，超过则内部滚动 */
  --pain-list-row: 35px;
  max-height: calc(var(--pain-list-row) * 15);
  overflow-x: hidden;
  overflow-y: auto;
}

.pain-list li {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: start;
  column-gap: 6px;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  line-height: 1.45;
}

.pain-list li:hover {
  background: #f8fafc;
}

.pain-list li.active {
  background: var(--el-color-primary-light-9);
}

.pain-dot {
  color: var(--el-color-primary);
  margin-right: 6px;
}

.pain-kw {
  font-weight: 500;
  min-width: 0;
  overflow-wrap: anywhere;
  word-break: break-word;
}

/** 不再固定高度：证据面板高度随展开/折叠和当前页内容自然变化，左侧维度列表（stretch）会同步变高 */
.evidence-list {
  flex: 1;
  min-height: 0;
  overflow: visible;
}

.evidence-block {
  padding: 12px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.evidence-block:last-child {
  border-bottom: none;
}

.evidence-block-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.evidence-time {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  min-width: 0;
}

.evidence-quote-wrap {
  margin-top: 0;
  min-width: 0;
}

.evidence-quote {
  font-size: 14px;
  line-height: 1.55;
  color: var(--el-text-color-primary);
  overflow-wrap: anywhere;
  word-break: break-word;
  white-space: pre-wrap;
  max-width: 100%;
}

.evidence-quote--collapsed {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  overflow: hidden;
  white-space: normal;
}

.evidence-toggle {
  flex-shrink: 0;
  margin: 0;
  padding: 0;
  border: none;
  background: none;
  color: var(--rsa-primary, var(--el-color-primary));
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
}

.evidence-toggle:hover {
  color: var(--rsa-primary-hover, var(--el-color-primary-light-3));
}

.evidence-quote :deep(mark) {
  background: #fef08a;
  padding: 0 2px;
  border-radius: 2px;
}

.evidence-pager {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 12px;
  flex-shrink: 0;
}

.pager-text {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  font-variant-numeric: tabular-nums;
}

.ai-insight-panel {
  margin-bottom: 16px;
}

.ai-insight-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.ai-insight-head .subpanel-title {
  margin: 0;
}


.ai-insight-body {
  font-size: 14px;
  line-height: 1.65;
  color: var(--el-text-color-primary);
  white-space: pre-wrap;
  word-break: break-word;
}

.ai-insight-list {
  margin: 0;
  padding-left: 1.15rem;
  font-size: 14px;
  line-height: 1.65;
  color: var(--el-text-color-primary);
}

.ai-insight-list li {
  margin-bottom: 8px;
}

.ai-insight-list li:last-child {
  margin-bottom: 0;
}

.ai-insight-empty {
  text-align: left;
  padding: 4px 0 0;
}
</style>
