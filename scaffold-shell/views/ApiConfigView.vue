<template>
  <div class="page">
    <el-card class="panel">
      <template #header>
        <div class="panel-header">
          <div>
            <h3>接口配置</h3>
            <p>维护平台对接接口、鉴权方式与调用状态。</p>
          </div>
          <el-button type="primary">新增接口</el-button>
        </div>
      </template>
      <el-table :data="rows" stripe>
        <el-table-column prop="name" label="接口名称" min-width="180" />
        <el-table-column prop="endpoint" label="Endpoint" min-width="250" />
        <el-table-column prop="method" label="请求方式" width="120" />
        <el-table-column prop="status" label="状态" width="120" />
        <el-table-column label="操作" width="180">
          <template #default>
            <el-button text type="primary">编辑</el-button>
            <el-button text>测试</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
const rows = [
  { name: '情感分析接口', endpoint: '/api/v1/sentiment/analyze', method: 'POST', status: '已启用' },
  { name: '痛点抽取接口', endpoint: '/api/v1/pain-points/extract', method: 'POST', status: '已启用' },
]
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
