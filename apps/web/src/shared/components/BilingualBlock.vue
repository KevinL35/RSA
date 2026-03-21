<template>
  <div class="bilingual-block">
    <div class="bilingual-en">{{ english }}</div>
    <template v-if="showSecondary">
      <div v-if="translation" class="bilingual-zh">{{ translation }}</div>
      <p v-if="translation" class="bilingual-hint">{{ t('translation.machineHint') }}</p>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { isEnglishLocale } from '../../app/i18n'

defineProps<{
  english: string
  translation?: string | null
}>()

const { t, locale } = useI18n()

const showSecondary = computed(() => !isEnglishLocale(locale.value as string))
</script>

<style scoped>
.bilingual-block {
  margin-bottom: 12px;
}
.bilingual-en {
  color: var(--el-text-color-primary);
  font-size: 14px;
  line-height: 1.5;
}
.bilingual-zh {
  margin-top: 6px;
  color: var(--el-text-color-regular);
  font-size: 13px;
  line-height: 1.55;
  white-space: pre-wrap;
}
.bilingual-hint {
  margin: 4px 0 0;
  font-size: 11px;
  color: var(--el-text-color-placeholder);
}
</style>
