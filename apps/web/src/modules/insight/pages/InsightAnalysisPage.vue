<template>
  <FeaturePlaceholderCard :title="t('insight.title')" :description="t('insight.desc')" />
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import FeaturePlaceholderCard from '../../../shared/components/FeaturePlaceholderCard.vue'

const { t } = useI18n()
</script>
