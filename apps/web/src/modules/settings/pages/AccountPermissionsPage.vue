<template>
  <div class="page">
    <el-card class="panel">
      <template #header>
        <div class="panel-header">
          <div>
            <h3>{{ t('settings.accTitle') }}</h3>
            <p>{{ t('settings.accDesc') }}</p>
          </div>
          <el-button type="primary">{{ t('settings.accAdd') }}</el-button>
        </div>
      </template>
      <el-table :data="rows" stripe>
        <el-table-column prop="username" :label="t('settings.accColUser')" min-width="160" />
        <el-table-column prop="name" :label="t('settings.accColName')" min-width="140" />
        <el-table-column prop="role" :label="t('settings.accColRole')" min-width="120" />
        <el-table-column prop="lastLogin" :label="t('settings.accColLast')" min-width="180" />
        <el-table-column prop="status" :label="t('settings.accColStatus')" width="120" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { locale, t } = useI18n()

const rows = computed(() => {
  if (locale.value === 'zh-CN') {
    return [
      {
        username: 'admin',
        name: '平台管理员',
        role: '超级管理员',
        lastLogin: '2026-03-20 09:31',
        status: '正常',
      },
      {
        username: 'analyst01',
        name: '数据分析师',
        role: '分析员',
        lastLogin: '2026-03-19 18:08',
        status: '正常',
      },
    ]
  }
  return [
    {
      username: 'admin',
      name: 'Admin',
      role: 'Super admin',
      lastLogin: '2026-03-20 09:31',
      status: 'Active',
    },
    {
      username: 'analyst01',
      name: 'Analyst',
      role: 'Analyst',
      lastLogin: '2026-03-19 18:08',
      status: 'Active',
    },
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
