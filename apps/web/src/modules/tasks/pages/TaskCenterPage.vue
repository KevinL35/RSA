<template>
  <el-card class="view-card" v-loading="loading">
    <template #header>
      <div class="card-head">
        <span>{{ t('taskCenter.title') }}</span>
        <div class="actions">
          <el-button type="primary" :loading="loading" @click="load">{{ t('taskCenter.refresh') }}</el-button>
        </div>
      </div>
    </template>

    <el-alert
      v-if="!canRetryTasks"
      type="info"
      :closable="false"
      show-icon
      :title="t('taskCenter.readOnlyHint')"
      style="margin-bottom: 12px"
    />

    <div class="filters">
      <el-select
        v-model="filterStatus"
        multiple
        collapse-tags
        collapse-tags-tooltip
        :placeholder="t('taskCenter.statusFilter')"
        clearable
        style="width: 260px"
      >
        <el-option :label="t('taskCenter.statusPending')" value="pending" />
        <el-option :label="t('taskCenter.statusRunning')" value="running" />
        <el-option :label="t('taskCenter.statusSuccess')" value="success" />
        <el-option :label="t('taskCenter.statusFailed')" value="failed" />
        <el-option :label="t('taskCenter.statusCancelled')" value="cancelled" />
      </el-select>
      <el-date-picker
        v-model="dateRange"
        type="datetimerange"
        :range-separator="t('taskCenter.rangeSep')"
        :start-placeholder="t('taskCenter.dateStart')"
        :end-placeholder="t('taskCenter.dateEnd')"
        value-format="YYYY-MM-DDTHH:mm:ss"
        style="max-width: 380px"
      />
      <el-input-number v-model="pageLimit" :min="1" :max="200" />
      <span class="hint">{{ t('taskCenter.perPage') }}</span>
      <el-button type="primary" plain @click="load">{{ t('taskCenter.applyFilter') }}</el-button>
    </div>

    <el-alert
      v-if="errorMsg"
      type="error"
      :closable="false"
      show-icon
      :title="errorMsg"
      style="margin: 14px 0"
    />

    <el-table :data="items" stripe style="width: 100%" :empty-text="t('taskCenter.empty')">
      <el-table-column prop="platform" :label="t('taskCenter.platform')" width="110" />
      <el-table-column
        prop="product_id"
        :label="t('taskCenter.productId')"
        min-width="140"
        show-overflow-tooltip
      />
      <el-table-column :label="t('taskCenter.status')" width="118">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)" size="small">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="t('taskCenter.duration')" width="100">
        <template #default="{ row }">
          {{ formatDuration(row.created_at, row.updated_at, row.status) }}
        </template>
      </el-table-column>
      <el-table-column
        prop="analysis_provider_id"
        :label="t('taskCenter.analysisProvider')"
        min-width="120"
        show-overflow-tooltip
      />
      <el-table-column :label="t('taskCenter.failureInfo')" min-width="220">
        <template #default="{ row }">
          <template v-if="row.status === 'failed'">
            <div class="fail-line">
              <span class="muted">{{ t('taskCenter.failureStage') }}</span>
              {{ row.error?.stage ?? row.failure_stage ?? '—' }}
            </div>
            <div class="fail-line">
              <span class="muted">{{ t('taskCenter.failureCode') }}</span>
              {{ row.error?.code ?? row.error_code ?? '—' }}
            </div>
            <div class="fail-msg">{{ row.error?.message ?? row.error_message ?? '—' }}</div>
          </template>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" :label="t('taskCenter.createdAt')" width="178" />
      <el-table-column :label="t('taskCenter.actions')" width="112" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'failed'"
            type="primary"
            link
            :disabled="!canRetryTasks || retryingId === row.id"
            :loading="retryingId === row.id"
            @click="onRetry(row)"
          >
            {{ t('taskCenter.retry') }}
          </el-button>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { fetchInsightTasks, postInsightTaskRetry } from '../api'
import type { InsightTaskRow } from '../types'
import { useAuthStore } from '../../auth/store/auth.store'

const { t } = useI18n()
const auth = useAuthStore()
const canRetryTasks = computed(() => auth.canRetryInsightTasks.value)
const loading = ref(false)
const items = ref<InsightTaskRow[]>([])
const errorMsg = ref('')
const filterStatus = ref<string[]>([])
const dateRange = ref<[string, string] | null>(null)
const pageLimit = ref(100)
const retryingId = ref<string | null>(null)

function statusTagType(s: string): 'info' | 'success' | 'warning' | 'danger' {
  if (s === 'success') return 'success'
  if (s === 'failed') return 'danger'
  if (s === 'running') return 'warning'
  return 'info'
}

function formatDuration(created: string, updated: string, status: string): string {
  const a = new Date(created).getTime()
  const b = new Date(updated).getTime()
  if (Number.isNaN(a) || Number.isNaN(b)) return '—'
  if (status === 'running' || status === 'pending') {
    const sec = Math.max(0, Math.floor((Date.now() - a) / 1000))
    return sec < 60 ? `~${sec}s` : `~${Math.floor(sec / 60)}m`
  }
  if (b < a) return '—'
  const sec = Math.floor((b - a) / 1000)
  if (sec < 60) return `${sec}s`
  const m = Math.floor(sec / 60)
  const s = sec % 60
  if (m < 60) return `${m}m${s}s`
  const h = Math.floor(m / 60)
  return `${h}h${m % 60}m`
}

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    const status = filterStatus.value.length > 0 ? filterStatus.value.join(',') : undefined
    let created_after: string | undefined
    let created_before: string | undefined
    if (dateRange.value?.length === 2) {
      created_after = dateRange.value[0]
      created_before = dateRange.value[1]
    }
    const res = await fetchInsightTasks({
      status,
      created_after,
      created_before,
      limit: pageLimit.value,
    })
    items.value = res.items ?? []
  } catch (e) {
    errorMsg.value = e instanceof Error ? e.message : String(e)
    items.value = []
  } finally {
    loading.value = false
  }
}

async function onRetry(row: InsightTaskRow) {
  if (!canRetryTasks.value) return
  retryingId.value = row.id
  try {
    const res = await postInsightTaskRetry(row.id)
    ElMessage.success(res.message || t('taskCenter.resetOk'))
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : String(e))
  } finally {
    retryingId.value = null
  }
}

onMounted(() => {
  void load()
})
</script>

<style scoped>
.view-card {
  border-radius: 10px;
  border: 1px solid #ebeef2;
  box-shadow: none;
}
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.actions {
  display: flex;
  gap: 8px;
}
.filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}
.hint {
  font-size: 13px;
  color: #64748b;
}
.fail-line {
  font-size: 12px;
  line-height: 1.4;
}
.fail-msg {
  font-size: 12px;
  color: #b91c1c;
  margin-top: 4px;
  word-break: break-word;
}
.muted {
  color: #94a3b8;
  font-size: 12px;
}
</style>
