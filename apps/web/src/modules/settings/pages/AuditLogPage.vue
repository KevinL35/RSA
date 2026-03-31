<template>
  <el-card class="view-card">
    <header class="page-header">
      <h2 class="page-title">{{ t('auditLog.title') }}</h2>
      <p class="page-subtitle">{{ t('auditLog.subtitle') }}</p>
    </header>

    <el-alert
      v-if="loadError"
      type="error"
      :closable="false"
      show-icon
      class="load-alert"
      :title="loadError"
    />

    <el-table v-loading="loading" :data="items" stripe empty-text="—" class="log-table">
      <el-table-column prop="username" :label="t('auditLog.colAccount')" min-width="120" />
      <el-table-column prop="created_at" :label="t('auditLog.colTime')" min-width="180">
        <template #default="{ row }">
          {{ formatTime(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column prop="menu_key" :label="t('auditLog.colMenu')" min-width="140">
        <template #default="{ row }">
          {{ menuLabel(row.menu_key) }}
        </template>
      </el-table-column>
      <el-table-column prop="message" :label="t('auditLog.colMessage')" min-width="280" show-overflow-tooltip />
    </el-table>

    <div v-if="total > 0" class="pager">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @current-change="load"
        @size-change="onSizeChange"
      />
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { fetchAuditLogs, type AuditLogRow } from '../auditLogApi'

const { t, te } = useI18n()

const loading = ref(false)
const loadError = ref('')
const items = ref<AuditLogRow[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)

const fmt = new Intl.DateTimeFormat(undefined, {
  dateStyle: 'short',
  timeStyle: 'medium',
})

function formatTime(iso: string) {
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? iso : fmt.format(d)
}

/** 与账号权限里存的 menu_keys（kebab）对齐到现有 menu.* 文案 */
const MENU_I18N: Record<string, string> = {
  login: 'menu.login',
  insight: 'menu.insight',
  'pain-audit': 'menu.painAudit',
  dictionary: 'menu.dictionary',
  'api-config': 'menu.apiConfig',
  'audit-log': 'menu.auditLog',
  'account-permissions': 'menu.accountPermissions',
}

function menuLabel(key: string) {
  const k = (key || '').trim()
  if (!k) return '—'
  const path = MENU_I18N[k] ?? `menu.${k}`
  if (te(path)) return t(path)
  return k
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const off = (page.value - 1) * pageSize.value
    const res = await fetchAuditLogs({ limit: pageSize.value, offset: off })
    items.value = res.items
    total.value = res.total
  } catch (e) {
    loadError.value = t('auditLog.loadFailed')
    items.value = []
    total.value = 0
    console.error(e)
  } finally {
    loading.value = false
  }
}

function onSizeChange() {
  page.value = 1
  void load()
}

onMounted(() => {
  void load()
})

watch(pageSize, () => {
  page.value = 1
})
</script>

<style scoped>
.view-card {
  border-radius: 10px;
  border: 1px solid #ebeef2;
  box-shadow: none;
}

.page-header {
  margin-bottom: 18px;
}

.page-title {
  margin: 0 0 8px;
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

.load-alert {
  margin-bottom: 14px;
}

.log-table {
  width: 100%;
}

.pager {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
