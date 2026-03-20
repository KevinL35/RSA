<template>
  <el-card class="view-card">
    <h3>{{ currentTitle }}</h3>
    <p>当前为 {{ currentTitle }} 占位页面，菜单和路由已经联通，替换为真实业务组件即可。</p>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { APP_MENUS } from '../config/menu.config'

const route = useRoute()
const currentTitle = computed(() => {
  for (const item of APP_MENUS) {
    if (item.path === route.path) return item.label
    const child = item.children?.find((x) => x.path === route.path)
    if (child) return child.label
  }
  return '业务模块'
})
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
