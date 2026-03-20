<template>
  <el-card class="view-card" v-loading="loading">
    <template #header>
      <div class="card-head">
        <span>任务中心</span>
        <div class="actions">
          <el-button type="primary" :loading="loading" @click="load">刷新</el-button>
        </div>
      </div>
    </template>
    <el-alert
      v-if="errorMsg"
      type="error"
      :closable="false"
      show-icon
      :title="errorMsg"
      style="margin-bottom: 14px"
    />
    <el-table :data="items" stripe style="width: 100%" empty-text="暂无数据（请先在 Supabase 执行迁移并创建任务）">
      <el-table-column prop="platform" label="平台" width="120" />
      <el-table-column prop="product_id" label="商品ID" min-width="160" show-overflow-tooltip />
      <el-table-column prop="status" label="状态" width="110" />
      <el-table-column prop="analysis_provider_id" label="分析源" min-width="140" show-overflow-tooltip />
      <el-table-column prop="error_message" label="错误信息" min-width="200" show-overflow-tooltip />
      <el-table-column prop="created_at" label="创建时间" width="200" />
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchInsightTasks } from '../api'
import type { InsightTaskRow } from '../types'

const loading = ref(false)
const items = ref<InsightTaskRow[]>([])
const errorMsg = ref('')

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await fetchInsightTasks()
    items.value = res.items ?? []
  } catch (e) {
    errorMsg.value = e instanceof Error ? e.message : String(e)
    items.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void load()
})
</script>

<style scoped>
.view-card { border-radius: 10px; border: 1px solid #ebeef2; box-shadow: none; }
.card-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.actions { display: flex; gap: 8px; }
</style>
