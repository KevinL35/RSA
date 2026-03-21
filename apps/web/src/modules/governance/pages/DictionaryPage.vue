<template>
  <FeaturePlaceholderCard :title="t('governance.dictionaryTitle')" :description="t('governance.dictionaryDesc')" />
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import FeaturePlaceholderCard from '../../../shared/components/FeaturePlaceholderCard.vue'

const { t } = useI18n()
</script>
