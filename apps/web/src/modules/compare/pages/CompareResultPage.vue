<template>
  <el-card class="view-card" v-loading="loading">
    <header class="page-header">
      <div class="page-header-body">
        <div class="page-header-title-row">
          <h2 class="page-title">{{ t('compare.resultPageTitle') }}</h2>
          <button type="button" class="rsa-text-back-btn" @click="goBack">
            {{ t('compare.resultBack') }}
          </button>
        </div>
        <p class="page-subtitle">{{ subtitle }}</p>
      </div>
    </header>

    <el-alert
      v-if="notFound"
      type="warning"
      :closable="false"
      show-icon
      :title="t('compare.resultNotFound')"
    />

    <template v-else>
      <el-alert v-if="failedMessage" type="error" :closable="false" show-icon :title="failedMessage" />

      <div v-else-if="result" class="result-block">
        <el-alert
          v-if="!uiEn && translationConfigured === false"
          type="info"
          :closable="false"
          show-icon
          :title="t('translation.notConfigured')"
          style="margin-bottom: 12px"
        />
        <p v-if="!uiEn" class="evidence-note">{{ t('translation.evidenceNote') }}</p>

        <h4>{{ t('compare.resultTitle') }}</h4>
        <ul class="cards">
          <li v-for="(c, i) in result.conclusion_cards" :key="i">
            <BilingualBlock
              :english="`${c.title} — ${c.detail}`"
              :translation="cardTranslations[i] || null"
            />
          </li>
        </ul>
        <h4>{{ t('compare.sentimentTitle') }}</h4>
        <pre class="json">{{ sentimentLine }}</pre>
      </div>
    </template>
  </el-card>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import BilingualBlock from '../../../shared/components/BilingualBlock.vue'
import { isEnglishLocale } from '../../../app/i18n'
import { translateAnalysisText } from '../../../shared/services/translateApi'
import type { CompareProductsResponse } from '../types'
import { fetchCompareRunDetail } from '../api'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()

const uiEn = computed(() => isEnglishLocale(locale.value as string))
const loading = ref(true)
const notFound = ref(false)
const result = ref<CompareProductsResponse | null>(null)
const failedMessage = ref('')

const cardTranslations = ref<string[]>([])
const translationConfigured = ref<boolean | null>(null)

const compareId = computed(() => {
  const p = route.params.compareId
  return typeof p === 'string' ? decodeURIComponent(p) : ''
})

const subtitle = computed(() => {
  void locale.value
  if (!result.value) return ''
  const { product_a: a, product_b: b } = result.value
  const left = `${a.platform} · ${a.product_id}`
  const right = `${b.platform} · ${b.product_id}`
  return t('compare.resultSubtitleVs', { a: left, b: right })
})

const sentimentLine = computed(() => {
  if (!result.value) return ''
  const { a, b } = result.value.sentiment
  return `A: +${a.positive} / ${a.neutral} / −${a.negative}\nB: +${b.positive} / ${b.neutral} / −${b.negative}`
})

watch(
  [result, locale],
  async () => {
    cardTranslations.value = []
    translationConfigured.value = null
    if (!result.value || uiEn.value) return
    const texts = result.value.conclusion_cards.map((c) => `${c.title}\n${c.detail}`)
    if (texts.length === 0) return
    const first = await translateAnalysisText(texts[0])
    translationConfigured.value = first.configured
    if (!first.configured) {
      cardTranslations.value = texts.map(() => '')
      return
    }
    const rest = await Promise.all(texts.slice(1).map((tx) => translateAnalysisText(tx)))
    cardTranslations.value = [first.translated ?? '', ...rest.map((r) => r.translated ?? '')]
  },
  { immediate: true },
)

function goBack() {
  void router.push('/compare-analysis')
}

async function hydrate() {
  loading.value = true
  notFound.value = false
  result.value = null
  failedMessage.value = ''
  const id = compareId.value
  try {
    if (!id) {
      notFound.value = true
      return
    }
    const row = await fetchCompareRunDetail(id)
    if (row.status === 'failed') {
      failedMessage.value = row.error_message || t('compare.statusFailed')
      return
    }
    if (row.result) {
      result.value = row.result as CompareProductsResponse
      return
    }
    notFound.value = true
  } catch {
    notFound.value = true
  } finally {
    loading.value = false
  }
}

watch(compareId, () => void hydrate(), { immediate: true })
</script>

<style scoped>
.view-card {
  border-radius: 10px;
  border: 1px solid #ebeef2;
  box-shadow: none;
  max-width: 920px;
}

.page-header {
  margin-bottom: 18px;
}

.page-header-body {
  min-width: 0;
}

.page-header-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.page-title {
  margin: 0;
  min-width: 0;
  flex: 1;
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

.result-block {
  margin-top: 8px;
}
.evidence-note {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin: 0 0 12px;
}
.cards {
  margin: 8px 0 16px;
  padding-left: 18px;
}
.json {
  background: var(--el-fill-color-light);
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 13px;
}
</style>
