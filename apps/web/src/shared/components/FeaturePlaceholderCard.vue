<template>
  <el-card class="view-card">
    <h3>{{ title }}</h3>
    <p>{{ description }}</p>
  </el-card>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  description: string
}>()
</script>

<style scoped>
.view-card {
  border-radius: 10px;
  border: 1px solid #ebeef2;
  box-shadow: none;
}

.view-card :deep(.el-card__body) {
  padding: 18px 20px;
}

.view-card h3 {
  margin: 0 0 10px;
  color: #111827;
  font-size: 18px;
}

.view-card p {
  margin: 0;
  color: #4b5563;
}
</style>
