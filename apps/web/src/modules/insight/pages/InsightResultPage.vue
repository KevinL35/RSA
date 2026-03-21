<template>
  <div class="result-page" v-loading="loading">
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

    <section class="result-header-card">
      <div class="result-header-body">
        <div class="result-header-title-row">
          <h1 class="result-main-title">{{ mainAsinTitle }}</h1>
          <button type="button" class="rsa-text-back-btn" @click="goBack">
            {{ t('insightResult.back') }}
          </button>
        </div>
        <p class="result-meta-line">{{ metaSubtitle }}</p>
      </div>
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

    <section class="split-row wordcloud-rank-row">
      <div class="panel half wordcloud-panel">
        <div class="wordcloud-panel-head">
          <h3 class="subpanel-title">{{ t('insightResult.wordCloudTitle') }}</h3>
          <el-select v-model="wordCloudDimension" class="wordcloud-dim-select" filterable>
            <el-option v-for="d in dimensionOrder" :key="d" :label="dimTitle(d)" :value="d" />
          </el-select>
        </div>
        <div class="wordcloud-body">
          <WordCloudChart
            v-if="wordCloudItems.length > 0"
            :items="wordCloudItems"
            :colors="wordCloudColors"
          />
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
          <el-select v-model="painListDimension" class="pain-list-dim-select" filterable>
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
        <h3 class="subpanel-title">{{ t('insightResult.evidenceTitle') }}</h3>
        <div class="evidence-list">
          <div v-if="!selectedKeyword" class="dim-empty evidence-hint">
            {{ t('insightResult.evidencePickKeyword') }}
          </div>
          <template v-else-if="paginatedEvidence.length">
            <div v-for="ev in paginatedEvidence" :key="String(ev.id)" class="evidence-block">
              <div class="evidence-block-head">
                <span class="evidence-time">{{ formatReviewDateTime(ev) }}</span>
                <button
                  v-if="evidenceLayoutFor(ev) === 'long'"
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
                <div
                  :ref="(el) => bindEvidenceQuoteEl(ev, el)"
                  class="evidence-quote"
                  :class="evidenceQuoteClass(ev)"
                  v-html="highlightEvidence(ev)"
                />
              </div>
            </div>
          </template>
          <div v-else class="dim-empty">{{ t('insightResult.evidenceEmpty') }}</div>
        </div>
        <div v-if="selectedKeyword && evidenceTotalPages > 1" class="evidence-pager">
          <el-button :disabled="evidencePage <= 1" @click="evidencePage--">{{ t('insightResult.prev') }}</el-button>
          <span class="pager-text">{{ t('insightResult.pageOf', { n: evidencePage, m: evidenceTotalPages }) }}</span>
          <el-button :disabled="evidencePage >= evidenceTotalPages" @click="evidencePage++">
            {{ t('insightResult.next') }}
          </el-button>
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
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { FullScreen } from '@element-plus/icons-vue'
import ReviewTrendChart from '../components/ReviewTrendChart.vue'
import WordCloudChart from '../components/WordCloudChart.vue'
import { fetchInsightDashboard } from '../api'
import type {
  Dimension6Key,
  InsightDashboardResponse,
  InsightEvidenceItem,
  PainRankItem,
  ReviewTimeseriesPoint,
} from '../dashboardTypes'

/** 证据评论实测布局：pending 测量中（先按三行裁剪）；short 不超过三行；long 超过三行可展开 */
type EvidenceQuoteLayout = 'pending' | 'short' | 'long'

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

/** 痛点排行榜仅统计「缺点」「退货原因」两维 */
const painRankingDimensions: Dimension6Key[] = ['cons', 'return_reasons']

/** 词云按维度着色（与六维卡片标签色系一致） */
const WORDCLOUD_PALETTES: Record<Dimension6Key, string[]> = {
  pros: ['#15803d', '#22c55e', '#4ade80', '#166534', '#86efac'],
  cons: ['#ca8a04', '#eab308', '#facc15', '#a16207', '#fde047'],
  return_reasons: ['#b91c1c', '#dc2626', '#ef4444', '#f87171', '#991b1b'],
  purchase_motivation: ['#1d4ed8', '#2563eb', '#3b82f6', '#60a5fa', '#1e40af'],
  user_expectation: ['#0e7490', '#0891b2', '#06b6d4', '#22d3ee', '#155e75'],
  usage_scenario: ['#4f46e5', '#6366f1', '#818cf8', '#4338ca', '#a5b4fc'],
}

const MOCK_DASHBOARD: InsightDashboardResponse = {
  insight_task_id: 'demo',
  platform: 'amazon',
  product_id: 'B0DEMO0001',
  task_status: 'success',
  analysis_provider_id: 'ins_builtin',
  analyzed_at: '2026-03-21T08:45:28.000Z',
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
  review_timeseries: [
    { date: '2026-03-01', count: 8 },
    { date: '2026-03-05', count: 14 },
    { date: '2026-03-10', count: 22 },
    { date: '2026-03-15', count: 18 },
    { date: '2026-03-20', count: 31 },
  ],
}

const loading = ref(false)
const errorMsg = ref('')
const dashboard = ref<InsightDashboardResponse | null>(null)

const taskId = computed(() => String(route.params.taskId || ''))
const isDemo = computed(() => taskId.value === 'demo')

const wordCloudDimension = ref<Dimension6Key>('cons')
const painListDimension = ref<Dimension6Key>('pros')
const selectedKeyword = ref<string | null>(null)
const evidencePage = ref(1)
const evidencePageSize = ref(5)

const expandVisible = ref(false)
const expandDim = ref<Dimension6Key | null>(null)

const evidenceExpandedIds = ref<Set<string>>(new Set())
const evidenceLayoutById = ref<Map<string, EvidenceQuoteLayout>>(new Map())

const emptyState = computed(() => dashboard.value?.empty_state ?? null)

function formatLocalDateTime(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso.replace('T', ' ').slice(0, 19)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

/** 主标题：商品 ID（如 ASIN） */
const mainAsinTitle = computed(() => {
  if (isDemo.value) return 'B0DEMO0001'
  const d = dashboard.value
  if (d?.product_id) return d.product_id
  const a = (route.query.asin as string | undefined)?.trim()
  return a || t('insightResult.productFallback')
})

/** 副标题仅展示短模型名：内置源统一 rsa-v1，其它为 analysis_provider_id（不用列表页「平台自研：…」长文案） */
const insightModelDisplay = computed(() => {
  if (isDemo.value) return 'rsa-v1'
  const id = dashboard.value?.analysis_provider_id
  if (id && String(id).trim() !== '' && id !== 'ins_builtin') return String(id).trim()
  return 'rsa-v1'
})

const analyzedAtFormatted = computed(() => {
  if (isDemo.value) return '2026-03-21 16:45:28'
  const iso = dashboard.value?.analyzed_at
  if (iso) return formatLocalDateTime(iso)
  const q = (route.query.analyzedAt as string | undefined)?.trim()
  if (q) return q
  return formatLocalDateTime(new Date().toISOString())
})

const metaSubtitle = computed(() =>
  t('insightResult.headerMetaLine', {
    model: insightModelDisplay.value,
    time: analyzedAtFormatted.value,
  }),
)

const reviewTrendPoints = computed((): ReviewTimeseriesPoint[] => dashboard.value?.review_timeseries ?? [])

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

const wordCloudItems = computed(() =>
  keywordsAggregatedForDimension(wordCloudDimension.value)
    .slice(0, 80)
    .map(({ keyword, count }) => ({ name: keyword, value: count })),
)

const dimensionListRows = computed(() => keywordsAggregatedForDimension(painListDimension.value).slice(0, 48))

const wordCloudColors = computed(() => WORDCLOUD_PALETTES[wordCloudDimension.value])

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

watch(painListDimension, () => {
  selectedKeyword.value = null
})

watch([selectedKeyword, painListDimension, evidencePage], () => {
  evidenceExpandedIds.value = new Set()
  evidenceLayoutById.value = new Map()
})

function evidenceLayoutFor(ev: InsightEvidenceItem): EvidenceQuoteLayout {
  return evidenceLayoutById.value.get(String(ev.id)) ?? 'pending'
}

function evidenceQuoteClass(ev: InsightEvidenceItem) {
  const layout = evidenceLayoutFor(ev)
  if (layout === 'short') return {}
  if (layout === 'long') {
    return { 'evidence-quote--collapsed': !isEvidenceExpanded(ev) }
  }
  return { 'evidence-quote--collapsed': true }
}

function bindEvidenceQuoteEl(ev: InsightEvidenceItem, el: unknown) {
  const id = String(ev.id)
  const html = el instanceof HTMLElement ? el : null
  if (!html) {
    const m = new Map(evidenceLayoutById.value)
    m.delete(id)
    evidenceLayoutById.value = m
    return
  }
  void nextTick(() => {
    requestAnimationFrame(() => {
      if (!html.isConnected) return
      void html.offsetHeight
      const overflow = html.scrollHeight > html.clientHeight + 2
      const m = new Map(evidenceLayoutById.value)
      m.set(id, overflow ? 'long' : 'short')
      evidenceLayoutById.value = m
    })
  })
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

function highlightEvidence(ev: InsightEvidenceItem) {
  const rawFull = typeof ev.review?.raw_text === 'string' ? ev.review.raw_text : ''
  const quote = typeof ev.evidence_quote === 'string' ? ev.evidence_quote : ''
  const raw = (rawFull.trim() || quote.trim()) || ''
  if (!raw) return ''
  let text = escapeHtml(raw)
  const kws = [...ev.keywords].sort((a, b) => b.length - a.length)
  for (const kw of kws) {
    if (!kw.trim()) continue
    const escaped = escapeHtml(kw).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const re = new RegExp(`(${escaped})`, 'gi')
    text = text.replace(re, '<mark>$1</mark>')
  }
  return text
}

async function load() {
  errorMsg.value = ''
  if (isDemo.value) {
    dashboard.value = MOCK_DASHBOARD
    painListDimension.value = 'pros'
    selectedKeyword.value = null
    return
  }
  loading.value = true
  try {
    dashboard.value = await fetchInsightDashboard(taskId.value, { evidence_limit: 120, evidence_offset: 0 })
    painListDimension.value = 'pros'
    selectedKeyword.value = null
  } catch (e) {
    errorMsg.value = e instanceof Error ? e.message : String(e)
    dashboard.value = null
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
</script>

<style scoped>
.result-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 8px 4px 32px;
}

.demo-banner,
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

.result-header-body {
  min-width: 0;
}

.result-header-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
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

.wordcloud-body :deep(.wordcloud-host) {
  flex: 1;
  min-height: 240px;
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
  grid-template-columns: minmax(260px, 300px) 1fr;
}

@media (max-width: 900px) {
  .evidence-row {
    grid-template-columns: 1fr;
  }
}

.pain-panel-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
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
}

.evidence-quote {
  font-size: 14px;
  line-height: 1.55;
  color: var(--el-text-color-primary);
  word-break: break-word;
}

.evidence-quote--collapsed {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  overflow: hidden;
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
  text-decoration: underline;
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
