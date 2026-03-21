<template>
  <div class="page">
    <el-card class="panel">
      <template #header>
        <div class="panel-header">
          <div>
            <h3>{{ t('settings.apiTitle') }}</h3>
            <p>{{ t('settings.apiDesc') }}</p>
          </div>
          <el-button type="primary">{{ t('settings.apiAdd') }}</el-button>
        </div>
      </template>
      <el-table :data="rows" stripe>
        <el-table-column prop="name" :label="t('settings.apiColName')" min-width="180" />
        <el-table-column prop="endpoint" :label="t('settings.apiColEndpoint')" min-width="250" />
        <el-table-column prop="method" :label="t('settings.apiColMethod')" width="120" />
        <el-table-column prop="status" :label="t('settings.apiColStatus')" width="120" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t, locale } = useI18n()

const rows = computed(() => {
  if (locale.value === 'zh-CN') {
    return [
      {
        name: '情感分析接口',
        endpoint: '/api/v1/sentiment/analyze',
        method: 'POST',
        status: '已启用',
      },
      {
        name: '痛点抽取接口',
        endpoint: '/api/v1/pain-points/extract',
        method: 'POST',
        status: '已启用',
      },
    ]
  }
  return [
    { name: 'Sentiment API', endpoint: '/api/v1/sentiment/analyze', method: 'POST', status: 'Enabled' },
    { name: 'Pain extraction API', endpoint: '/api/v1/pain-points/extract', method: 'POST', status: 'Enabled' },
  ]
})
</script>

<style scoped>
.page {
  height: 100%;
}
.panel {
  border-radius: 10px;
  border: 1px solid #ebeef2;
  box-shadow: none;
}
.panel :deep(.el-card__header) {
  padding: 14px 18px;
  border-bottom: 1px solid #f2f4f7;
}
.panel :deep(.el-card__body) {
  padding: 12px 18px 16px;
}
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.panel-header h3 {
  margin: 0;
  color: #111827;
  font-size: 18px;
}
.panel-header p {
  margin: 6px 0 0;
  color: #6b7280;
}
</style>
