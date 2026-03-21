<template>
  <el-card class="view-card" v-loading="loading">
    <template #header>
      <div class="card-head">
        <span>{{ t('compare.title') }}</span>
        <span class="muted">{{ t('compare.subtitle') }}</span>
      </div>
    </template>

    <el-form label-width="100px" class="compare-form" @submit.prevent="runCompare">
      <div class="pair">
        <div class="pair-title">{{ t('compare.productA') }}</div>
        <el-form-item :label="t('compare.platform')">
          <el-input v-model="platformA" :placeholder="t('compare.platformPh')" clearable />
        </el-form-item>
        <el-form-item :label="t('compare.productId')">
          <el-input v-model="productIdA" :placeholder="t('compare.productIdPh')" clearable />
        </el-form-item>
      </div>
      <div class="pair">
        <div class="pair-title">{{ t('compare.productB') }}</div>
        <el-form-item :label="t('compare.platform')">
          <el-input v-model="platformB" :placeholder="t('compare.platformPh')" clearable />
        </el-form-item>
        <el-form-item :label="t('compare.productId')">
          <el-input v-model="productIdB" :placeholder="t('compare.productIdPh')" clearable />
        </el-form-item>
      </div>
      <el-form-item>
        <el-button type="primary" :loading="loading" native-type="submit">{{ t('compare.compareBtn') }}</el-button>
        <router-link class="task-link" to="/task-center">{{ t('compare.goTaskCenter') }}</router-link>
      </el-form-item>
    </el-form>

    <el-alert
      v-if="prereqError"
      type="warning"
      :closable="false"
      show-icon
      class="pre-alert"
    >
      <template #title>{{ t('compare.cannotCompare') }}</template>
      <div class="pre-body">
        <p class="pre-line">{{ prereqLine }}</p>
        <p class="pre-hint">{{ prereqGuide }}</p>
        <router-link class="task-link" :to="prereqError.next_step.route">
          {{ prereqLinkLabel }}
        </router-link>
      </div>
    </el-alert>

    <el-alert v-else-if="genericError" type="error" :closable="false" show-icon :title="genericError" />

    <div v-if="result" class="result-block">
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
  </el-card>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import BilingualBlock from '../../../shared/components/BilingualBlock.vue'
import { isEnglishLocale } from '../../../app/i18n'
import { translateAnalysisText } from '../../../shared/services/translateApi'
import { ComparePrerequisiteError, fetchCompareProducts } from '../api'
import type { ComparePrerequisiteErrorDetail, CompareProductsResponse } from '../types'

const { t, locale } = useI18n()

const uiEn = computed(() => isEnglishLocale(locale.value as string))

const platformA = ref('amazon')
const productIdA = ref('')
const platformB = ref('amazon')
const productIdB = ref('')

const loading = ref(false)
const prereqError = ref<ComparePrerequisiteErrorDetail | null>(null)
const genericError = ref('')
const result = ref<CompareProductsResponse | null>(null)

const cardTranslations = ref<string[]>([])
const translationConfigured = ref<boolean | null>(null)

const prereqLine = computed(() => {
  if (!prereqError.value) return ''
  return uiEn.value ? prereqError.value.messages.en : prereqError.value.messages.zh_CN
})
const prereqGuide = computed(() => {
  if (!prereqError.value) return ''
  return uiEn.value ? prereqError.value.guidance.en : prereqError.value.guidance.zh_CN
})
const prereqLinkLabel = computed(() => {
  if (!prereqError.value) return ''
  return uiEn.value ? prereqError.value.next_step.label_en : prereqError.value.next_step.label_zh
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

async function runCompare() {
  prereqError.value = null
  genericError.value = ''
  result.value = null
  loading.value = true
  try {
    result.value = await fetchCompareProducts({
      platform_a: platformA.value,
      product_id_a: productIdA.value,
      platform_b: platformB.value,
      product_id_b: productIdB.value,
    })
  } catch (e) {
    if (e instanceof ComparePrerequisiteError) {
      prereqError.value = e.detail
    } else if (e instanceof Error) {
      genericError.value = e.message
    } else {
      genericError.value = String(e)
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.view-card {
  max-width: 920px;
}
.card-head {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.muted {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  font-weight: normal;
}
.compare-form {
  max-width: 560px;
}
.pair {
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.pair-title {
  font-weight: 600;
  margin-bottom: 8px;
}
.task-link {
  margin-left: 12px;
  font-size: 14px;
}
.pre-alert {
  margin-top: 8px;
}
.pre-body {
  line-height: 1.55;
}
.pre-line {
  white-space: pre-wrap;
  margin: 0 0 8px;
}
.pre-hint {
  margin: 0 0 8px;
  color: var(--el-text-color-regular);
}
.result-block {
  margin-top: 20px;
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
