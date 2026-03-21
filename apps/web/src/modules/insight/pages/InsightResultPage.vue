<template>
  <div class="result-page" v-loading="loading">
    <div class="result-toolbar">
      <el-button type="primary" link @click="goBack">{{ t('insightResult.back') }}</el-button>
    </div>

    <el-alert
      v-if="isDemo"
      type="info"
      :closable="false"
      show-icon
      class="demo-banner"
      :title="t('insightResult.demoBanner')"
    />
    <el-alert
      v-if="errorMsg"
      type="error"
      :closable="false"
      show-icon
      class="err-banner"
      :title="errorMsg"
    />
    <el-alert
      v-if="emptyState && !isDemo"
      type="warning"
      :closable="false"
      show-icon
      class="err-banner"
      :title="emptyState.message"
      :description="emptyState.hint"
    />

    <section class="product-bar">
      <div class="product-main">
        <h1 class="product-title">{{ productTitle }}</h1>
        <div class="product-meta">
          <span v-if="asinDisplay">ASIN {{ asinDisplay }}</span>
          <span v-if="countryDisplay">{{ countryDisplay }}</span>
          <span v-if="ratingDisplay">{{ ratingDisplay }}</span>
          <span v-if="reviewsDisplay">{{ reviewsDisplay }}</span>
        </div>
      </div>
    </section>

    <section class="ai-bar">
      <span class="ai-label">{{ t('insightResult.aiAnalysis') }}</span>
      <span class="ai-meta">{{ modelDisplay }}</span>
      <span class="ai-meta">{{ t('insightResult.analyzedAt') }}：{{ analyzedAtDisplay }}</span>
    </section>

    <section class="dim-grid">
      <div v-for="dim in dimensionOrder" :key="dim" class="dim-card">
        <div class="dim-card-head">
          <span class="dim-tag" :class="`dim-tag--${dim}`">{{ dimTitle(dim) }}</span>
          <div class="dim-card-head-right">
            <span class="dim-metric-label">{{ t('insightResult.cardReviewCount') }}</span>
            <span class="dim-metric-label">{{ t('insightResult.cardShare') }}</span>
            <el-button
              type="primary"
              link
              class="dim-expand"
              :icon="FullScreen"
              @click="openCardExpand(dim)"
            />
          </div>
        </div>
        <div class="dim-card-body">
          <template v-if="cardRows(dim).length">
            <div v-for="(row, idx) in cardRows(dim)" :key="idx" class="dim-row">
              <span class="dim-row-label" :title="row.label">{{ row.label }}</span>
              <span class="dim-row-num">{{ row.count }}</span>
              <span class="dim-row-num">{{ row.pct }}%</span>
            </div>
          </template>
          <div v-else class="dim-empty">{{ t('insightResult.cardEmpty') }}</div>
        </div>
      </div>
    </section>

    <section class="panel rank-panel">
      <div class="panel-head">
        <h2 class="panel-title">{{ t('insightResult.rankTitle') }}</h2>
        <div class="panel-filters">
          <el-select v-model="rankDimFilter" style="width: 160px">
            <el-option :label="t('insightResult.allDimensions')" value="all" />
            <el-option v-for="d in dimensionOrder" :key="d" :label="dimTitle(d)" :value="d" />
          </el-select>
          <el-select v-model="rankSort" style="width: 160px">
            <el-option :label="t('insightResult.sortScore')" value="score" />
            <el-option :label="t('insightResult.sortFreq')" value="freq" />
            <el-option :label="t('insightResult.sortKeyword')" value="keyword" />
          </el-select>
        </div>
      </div>
      <el-table :data="rankingTableRows" stripe class="rank-table" max-height="320">
        <el-table-column prop="dimensionLabel" :label="t('insightResult.colDimension')" width="120" />
        <el-table-column prop="keyword" :label="t('insightResult.colPain')" min-width="160" show-overflow-tooltip />
        <el-table-column prop="score" :label="t('insightResult.colScore')" width="88" />
        <el-table-column prop="freq" :label="t('insightResult.colFreq')" width="88" />
        <el-table-column prop="sentiment" :label="t('insightResult.colSentiment')" width="100" />
        <el-table-column prop="trend" :label="t('insightResult.colTrend')" width="72" align="center" />
      </el-table>
    </section>

    <section class="split-row">
      <div class="panel half">
        <h3 class="subpanel-title">{{ t('insightResult.wordCloudTitle') }}</h3>
        <div class="placeholder-box">{{ t('insightResult.wordCloudPlaceholder') }}</div>
      </div>
      <div class="panel half">
        <h3 class="subpanel-title">{{ t('insightResult.trendTitle') }}</h3>
        <div class="placeholder-box">{{ t('insightResult.trendPlaceholder') }}</div>
      </div>
    </section>

    <section class="split-row evidence-row">
      <div class="panel pain-panel">
        <h3 class="subpanel-title">{{ t('insightResult.painListTitle') }}</h3>
        <ul class="pain-list">
          <li
            v-for="r in rankingTableRows.slice(0, 24)"
            :key="r.keyword + r.dimensionLabel"
            :class="{ active: selectedKeyword === r.keyword }"
            @click="selectedKeyword = r.keyword"
          >
            <span class="pain-dot">●</span>
            <span class="pain-kw">{{ r.keyword }}</span>
            <span class="pain-dim">({{ r.dimensionLabel }})</span>
          </li>
        </ul>
      </div>
      <div class="panel evidence-panel">
        <h3 class="subpanel-title">{{ t('insightResult.evidenceTitle') }}</h3>
        <div class="evidence-list">
          <template v-if="paginatedEvidence.length">
            <div v-for="ev in paginatedEvidence" :key="String(ev.id)" class="evidence-block">
              <div class="evidence-meta">
                review {{ shortReviewId(ev.review_id) }}
                <span v-if="reviewRating(ev) != null"> · {{ stars(reviewRating(ev)!) }}</span>
                <span v-if="reviewDate(ev)"> · {{ reviewDate(ev) }}</span>
              </div>
              <div class="evidence-quote" v-html="highlightEvidence(ev)" />
            </div>
          </template>
          <div v-else class="dim-empty">{{ t('insightResult.evidenceEmpty') }}</div>
        </div>
        <div v-if="evidenceTotalPages > 1" class="evidence-pager">
          <el-button :disabled="evidencePage <= 1" @click="evidencePage--">{{ t('insightResult.prev') }}</el-button>
          <span class="pager-text">{{ t('insightResult.pageOf', { n: evidencePage, m: evidenceTotalPages }) }}</span>
          <el-button :disabled="evidencePage >= evidenceTotalPages" @click="evidencePage++">
            {{ t('insightResult.next') }}
          </el-button>
        </div>
      </div>
    </section>

    <el-dialog v-model="expandVisible" :title="expandTitle" width="640px" destroy-on-close>
      <el-table :data="expandRows" stripe max-height="420">
        <el-table-column prop="label" :label="t('insightResult.colPain')" min-width="200" show-overflow-tooltip />
        <el-table-column prop="count" :label="t('insightResult.cardReviewCount')" width="100" />
        <el-table-column prop="pct" :label="t('insightResult.cardShare')" width="88">
          <template #default="{ row }">{{ row.pct }}%</template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { FullScreen } from '@element-plus/icons-vue'
import { fetchInsightDashboard } from '../api'
import type { Dimension6Key, InsightDashboardResponse, InsightEvidenceItem, PainRankItem } from '../dashboardTypes'
import { insightApiConfigRows } from '../../settings/apiConfig.shared'
import { formatInsightModelLine } from '../../../shared/utils/insightModelLabel'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const dimensionOrder: Dimension6Key[] = [
  'pros',
  'cons',
  'return_reasons',
  'purchase_motivation',
  'user_expectation',
  'usage_scenario',
]

const MOCK_DASHBOARD: InsightDashboardResponse = {
  insight_task_id: 'demo',
  platform: 'amazon',
  product_id: 'B0DEMO0001',
  task_status: 'success',
  empty_state: null,
  dimension_counts: {
    pros: 186,
    cons: 312,
    return_reasons: 48,
    purchase_motivation: 124,
    user_expectation: 96,
    usage_scenario: 88,
  },
  pain_ranking: [
    { keyword: 'fast charging', count: 142, dimensions: ['pros'] },
    { keyword: 'compact design', count: 118, dimensions: ['pros'] },
    { keyword: 'good build quality', count: 96, dimensions: ['pros'] },
    { keyword: 'battery life', count: 186, dimensions: ['cons'] },
    { keyword: 'charging speed', count: 124, dimensions: ['cons'] },
    { keyword: 'heat under load', count: 76, dimensions: ['cons'] },
    { keyword: 'not as described', count: 28, dimensions: ['return_reasons'] },
    { keyword: 'gift for travel', count: 64, dimensions: ['purchase_motivation'] },
    { keyword: 'longer cable', count: 52, dimensions: ['user_expectation'] },
    { keyword: 'office desk setup', count: 58, dimensions: ['usage_scenario'] },
  ],
  evidence: {
    items: [
      {
        id: 'e1',
        dimension: 'cons',
        keywords: ['battery life'],
        evidence_quote: 'The battery drains faster than expected when using multiple ports.',
        highlight_spans: [],
        review_id: 'rev-demo-8821',
        insight_task_id: 'demo',
        review: { raw_text: 'The battery drains faster than expected when using multiple ports.', rating: 3, reviewed_at: '2026-03-10' },
      },
      {
        id: 'e2',
        dimension: 'cons',
        keywords: ['battery life'],
        evidence_quote: 'Not happy with battery life under heavy load.',
        highlight_spans: [],
        review_id: 'rev-demo-8750',
        insight_task_id: 'demo',
        review: { raw_text: 'Not happy with battery life under heavy load.', rating: 2, reviewed_at: '2026-03-09' },
      },
      {
        id: 'e3',
        dimension: 'pros',
        keywords: ['fast charging'],
        evidence_quote: 'Charges my phone incredibly fast, very satisfied.',
        highlight_spans: [],
        review_id: 'rev-demo-8601',
        insight_task_id: 'demo',
        review: { raw_text: 'Charges my phone incredibly fast, very satisfied.', rating: 5, reviewed_at: '2026-03-08' },
      },
    ],
    total: 3,
    limit: 50,
    offset: 0,
  },
}

const loading = ref(false)
const errorMsg = ref('')
const dashboard = ref<InsightDashboardResponse | null>(null)

const taskId = computed(() => String(route.params.taskId || ''))
const isDemo = computed(() => taskId.value === 'demo')

const rankDimFilter = ref<string>('all')
const rankSort = ref<'score' | 'freq' | 'keyword'>('score')
const selectedKeyword = ref<string | null>(null)
const evidencePage = ref(1)
const evidencePageSize = ref(5)

const expandVisible = ref(false)
const expandDim = ref<Dimension6Key | null>(null)

const emptyState = computed(() => dashboard.value?.empty_state ?? null)

const productTitle = computed(() => {
  const q = route.query.title as string | undefined
  if (q) return q
  const d = dashboard.value
  if (d?.product_id) return `${d.platform} · ${d.product_id}`
  return t('insightResult.productFallback')
})

const asinDisplay = computed(() => (route.query.asin as string) || dashboard.value?.product_id || '')
const countryDisplay = computed(() => route.query.country as string)
const ratingDisplay = computed(() => {
  const r = route.query.rating as string
  return r && r !== '0' ? `★ ${r}` : ''
})
const reviewsDisplay = computed(() => {
  const n = route.query.reviews as string
  return n ? t('insightResult.reviewsCount', { n }) : ''
})

const modelDisplay = computed(() => {
  const q = (route.query.model as string | undefined)?.trim()
  if (q) return q
  if (isDemo.value) {
    return formatInsightModelLine(
      { name: t('insight.demoInsightProviderName'), model: 'deepseek-chat' },
      t,
    )
  }
  const builtin = insightApiConfigRows.value.find((r) => r.id === 'ins_builtin')
  if (builtin) return formatInsightModelLine(builtin, t)
  return t('insight.defaultAnalysisProvider')
})
const analyzedAtDisplay = computed(() => {
  const q = route.query.analyzedAt as string
  if (q) return q
  return new Date().toISOString().slice(0, 16).replace('T', ' ')
})

function dimTitle(dim: Dimension6Key) {
  return t(`insightResult.dim.${dim}`)
}

function goBack() {
  router.push('/insight-analysis')
}

function painForDimension(dim: Dimension6Key, list: PainRankItem[]) {
  return list.filter((p) => p.dimensions.includes(dim))
}

function cardRows(dim: Dimension6Key): { label: string; count: number; pct: number }[] {
  const dash = dashboard.value
  if (!dash) return []
  const items = painForDimension(dim, dash.pain_ranking)
  const sum = items.reduce((s, x) => s + x.count, 0) || 1
  return items.map((x) => ({
    label: x.keyword,
    count: x.count,
    pct: Math.round((x.count / sum) * 100),
  }))
}

function rankScore(count: number) {
  return Math.min(99, Math.round(32 + count * 0.35))
}

function primaryDimension(dims: string[]): Dimension6Key {
  for (const d of dimensionOrder) {
    if (dims.includes(d)) return d
  }
  return 'pros'
}

function sentimentLabel(dims: string[]) {
  if (dims.some((d) => d === 'cons' || d === 'return_reasons')) return t('insightResult.sentimentNeg')
  if (dims.includes('pros')) return t('insightResult.sentimentPos')
  return t('insightResult.sentimentMix')
}

function trendForKeyword(kw: string) {
  let h = 0
  for (let i = 0; i < kw.length; i++) h = (h + kw.charCodeAt(i) * (i + 1)) % 3
  return h === 0 ? '↑' : h === 1 ? '→' : '↓'
}

const rankingTableRows = computed(() => {
  const dash = dashboard.value
  if (!dash) return []
  let list = [...dash.pain_ranking]
  const f = rankDimFilter.value
  if (f && f !== 'all') list = list.filter((p) => p.dimensions.includes(f))
  if (rankSort.value === 'keyword') {
    list.sort((a, b) => a.keyword.localeCompare(b.keyword))
  } else if (rankSort.value === 'freq') {
    list.sort((a, b) => b.count - a.count)
  } else {
    list.sort((a, b) => rankScore(b.count) - rankScore(a.count))
  }
  return list.map((p) => {
    const dim = primaryDimension(p.dimensions)
    return {
      dimensionLabel: dimTitle(dim),
      keyword: p.keyword,
      score: rankScore(p.count),
      freq: p.count,
      sentiment: sentimentLabel(p.dimensions),
      trend: trendForKeyword(p.keyword),
    }
  })
})

const filteredEvidence = computed(() => {
  const dash = dashboard.value
  if (!dash) return []
  const items = dash.evidence.items
  const kw = selectedKeyword.value
  if (!kw) return items
  const lower = kw.toLowerCase()
  return items.filter((ev) => ev.keywords.some((k) => k.toLowerCase() === lower))
})

const evidenceTotalPages = computed(() =>
  Math.max(1, Math.ceil(filteredEvidence.value.length / evidencePageSize.value)),
)

const paginatedEvidence = computed(() => {
  const start = (evidencePage.value - 1) * evidencePageSize.value
  return filteredEvidence.value.slice(start, start + evidencePageSize.value)
})

watch([selectedKeyword, () => filteredEvidence.value.length], () => {
  evidencePage.value = 1
})

const expandRows = computed(() => (expandDim.value ? cardRows(expandDim.value) : []))
const expandTitle = computed(() => (expandDim.value ? dimTitle(expandDim.value) : ''))

function openCardExpand(dim: Dimension6Key) {
  expandDim.value = dim
  expandVisible.value = true
}

function shortReviewId(id: string) {
  return id.length > 14 ? `${id.slice(0, 10)}…` : id
}

function reviewRating(ev: InsightEvidenceItem): number | null {
  const r = ev.review?.rating
  return typeof r === 'number' ? r : null
}

function reviewDate(ev: InsightEvidenceItem): string {
  const raw = ev.review?.reviewed_at
  return typeof raw === 'string' ? raw.slice(0, 10) : ''
}

function stars(n: number) {
  const f = Math.max(0, Math.min(5, Math.round(n)))
  return '★'.repeat(f) + '☆'.repeat(5 - f)
}

function escapeHtml(s: string) {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function highlightEvidence(ev: InsightEvidenceItem) {
  const fromReview = typeof ev.review?.raw_text === 'string' ? ev.review.raw_text : ''
  const raw = ev.evidence_quote || fromReview || ''
  let text = escapeHtml(raw)
  const kws = [...ev.keywords].sort((a, b) => b.length - a.length)
  for (const kw of kws) {
    if (!kw.trim()) continue
    const re = new RegExp(`(${escapeHtml(kw).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi')
    text = text.replace(re, '<mark>$1</mark>')
  }
  return `"${text}"`
}

async function load() {
  errorMsg.value = ''
  if (isDemo.value) {
    dashboard.value = MOCK_DASHBOARD
    return
  }
  loading.value = true
  try {
    dashboard.value = await fetchInsightDashboard(taskId.value, { evidence_limit: 120, evidence_offset: 0 })
  } catch (e) {
    errorMsg.value = e instanceof Error ? e.message : String(e)
    dashboard.value = null
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
</script>

<style scoped>
.result-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 8px 4px 32px;
}

.result-toolbar {
  margin-bottom: 12px;
}

.demo-banner,
.err-banner {
  margin-bottom: 12px;
}

.product-bar {
  background: #fff;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  padding: 16px 20px;
  margin-bottom: 12px;
}

.product-title {
  margin: 0 0 8px;
  font-size: 18px;
  font-weight: 600;
  line-height: 1.35;
}

.product-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.ai-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
  padding: 10px 16px;
  background: #f8fafc;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;
  margin-bottom: 20px;
  font-size: 13px;
}

.ai-label {
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.ai-meta {
  color: var(--el-text-color-regular);
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
  display: flex;
  align-items: center;
  gap: 12px;
}

.dim-metric-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.dim-expand {
  padding: 4px;
  min-height: auto;
}

.dim-tag {
  display: inline-block;
  font-size: 12px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 4px;
}

.dim-tag--pros {
  color: #166534;
  background: #dcfce7;
}
.dim-tag--cons {
  color: #a16207;
  background: #fef9c3;
}
.dim-tag--return_reasons {
  color: #b91c1c;
  background: #fee2e2;
}
.dim-tag--purchase_motivation {
  color: #1d4ed8;
  background: #dbeafe;
}
.dim-tag--user_expectation {
  color: #0e7490;
  background: #cffafe;
}
.dim-tag--usage_scenario {
  color: #4338ca;
  background: #e0e7ff;
}

.dim-card-body {
  max-height: 220px;
  overflow-y: auto;
  padding: 8px 12px 10px;
}

.dim-row {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 10px;
  align-items: start;
  font-size: 13px;
  padding: 8px 0;
  border-bottom: 1px solid #f1f5f9;
}

.dim-row:last-child {
  border-bottom: none;
}

.dim-row-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dim-row-num {
  color: var(--el-text-color-regular);
  font-variant-numeric: tabular-nums;
  min-width: 36px;
  text-align: right;
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

.rank-panel .panel-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.panel-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.panel-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
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
  grid-template-columns: 280px 1fr;
}

@media (max-width: 900px) {
  .evidence-row {
    grid-template-columns: 1fr;
  }
}

.pain-list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 360px;
  overflow-y: auto;
}

.pain-list li {
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  line-height: 1.4;
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
}

.pain-dim {
  color: var(--el-text-color-secondary);
  margin-left: 6px;
  font-size: 12px;
}

.evidence-list {
  min-height: 120px;
}

.evidence-block {
  padding: 12px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.evidence-block:last-child {
  border-bottom: none;
}

.evidence-meta {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 6px;
}

.evidence-quote {
  font-size: 14px;
  line-height: 1.55;
  color: var(--el-text-color-primary);
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
}

.pager-text {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
</style>
