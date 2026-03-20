<template>
  <div class="page">
    <el-card class="panel">
      <template #header>
        <div class="panel-header">
          <div>
            <h3>账号权限</h3>
            <p>管理平台账号、角色权限与登录状态。</p>
          </div>
          <el-button type="primary">新增账号</el-button>
        </div>
      </template>
      <el-table :data="rows" stripe>
        <el-table-column prop="username" label="账号" min-width="160" />
        <el-table-column prop="name" label="姓名" min-width="140" />
        <el-table-column prop="role" label="角色" min-width="120" />
        <el-table-column prop="lastLogin" label="最近登录" min-width="180" />
        <el-table-column prop="status" label="状态" width="120" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
const rows = [
  { username: 'admin', name: '平台管理员', role: '超级管理员', lastLogin: '2026-03-20 09:31', status: '正常' },
  { username: 'analyst01', name: '数据分析师', role: '分析员', lastLogin: '2026-03-19 18:08', status: '正常' },
]
</script>

<style scoped>
.page { height: 100%; }
.panel { border-radius: 10px; border: 1px solid #ebeef2; box-shadow: none; }
.panel :deep(.el-card__header) { padding: 14px 18px; border-bottom: 1px solid #f2f4f7; }
.panel :deep(.el-card__body) { padding: 12px 18px 16px; }
.panel-header { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.panel-header h3 { margin: 0; color: #111827; font-size: 18px; }
.panel-header p { margin: 6px 0 0; color: #6b7280; }
</style>
