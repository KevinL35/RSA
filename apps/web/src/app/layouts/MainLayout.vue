<template>
  <div class="layout-shell">
    <aside class="sidebar" :class="{ collapsed }">
      <div class="sidebar-top">
        <el-button class="icon-btn" @click="collapsed = !collapsed">
          <span class="menu-icon" v-html="menuActionSvg" />
        </el-button>
        <div v-show="!collapsed" class="brand-text">
          <strong>{{ t('brand.full') }}</strong>
        </div>
      </div>

      <el-scrollbar class="menu-wrap">
        <el-menu
          :default-active="activePath"
          :default-openeds="defaultOpeneds"
          :collapse="collapsed"
          :collapse-transition="false"
          class="shell-menu"
          @select="onSelect"
        >
          <template v-for="item in menus" :key="item.key">
            <el-sub-menu v-if="item.children?.length && !collapsed" :index="item.key">
              <template #title>
                <span class="menu-icon" v-html="item.icon" />
                <span class="menu-label">{{ t(item.labelKey) }}</span>
              </template>
              <el-menu-item v-for="child in item.children" :key="child.key" :index="child.path">
                {{ t(child.labelKey) }}
              </el-menu-item>
            </el-sub-menu>
            <el-menu-item v-else :index="item.path">
              <span class="menu-icon" v-html="item.icon" />
              <template #title>
                <span class="menu-label">{{ t(item.labelKey) }}</span>
              </template>
            </el-menu-item>
          </template>
        </el-menu>
      </el-scrollbar>

      <div class="sidebar-bottom">
        <el-button class="logout-btn" @click="onLogout">
          <span class="menu-icon" v-html="logoutSvg" />
        </el-button>
      </div>
    </aside>

    <main class="main">
      <div class="main-inner">
        <router-view />
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { APP_MENUS, type MenuItem } from '../config/menu.config'
import { isPlatformMenuAuth, useAuthStore } from '../../modules/auth/store/auth.store'

const { t } = useI18n()

const collapsed = ref(false)
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

function menuVisible(item: MenuItem): boolean {
  if (isPlatformMenuAuth()) {
    // 依赖 auth.menuKeys，账号权限保存后会触发重算（勿仅用 getStoredMenuKeys，否则非响应式）
    const keys = auth.menuKeys.value
    if (keys.length === 0) return false
    return keys.includes(item.key)
  }
  if (!item.allowedRoles?.length) return true
  return item.allowedRoles.includes(auth.role.value)
}

const menus = computed(() =>
  APP_MENUS.filter(menuVisible).map((item) => {
    if (!item.children?.length) return item
    const children = item.children.filter(menuVisible)
    return { ...item, children }
  }),
)

const activePath = computed(() => route.path)
const defaultOpeneds = computed(() => {
  const parent = menus.value.find((item) => item.children?.some((child) => child.path === route.path))
  return parent ? [parent.key] : []
})
const menuActionSvg =
  '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><g stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M5 7h14"></path><path d="M5 12h14"></path><path d="M5 17h10"></path></g></svg>'
const logoutSvg =
  '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-log-out-icon lucide-log-out"><path d="m16 17 5-5-5-5"/><path d="M21 12H9"/><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/></svg>'

function onSelect(path: string) {
  router.push(path)
}

async function onLogout() {
  await ElMessageBox.confirm(t('layout.logoutConfirm'), t('layout.logoutTitle'), { type: 'warning' })
  auth.logout()
  router.replace('/login')
}
</script>

<style scoped>
.layout-shell {
  display: flex;
  height: 100vh;
  background: var(--rsa-bg);
}

.sidebar {
  display: flex;
  flex-direction: column;
  width: 244px;
  padding: 14px 12px;
  box-sizing: border-box;
  transition:
    width 0.2s ease,
    padding 0.2s ease;
  background: #fff;
  border-right: 1px solid var(--rsa-border);
}

.sidebar.collapsed {
  width: 80px;
  padding-left: 10px;
  padding-right: 10px;
  --collapsed-axis-offset-x: -10px;
}

.sidebar-top {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 10px;
  padding: 0 8px;
}

.brand-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
  color: var(--rsa-text-main);
}

.brand-text strong {
  font-size: 17px;
  line-height: 1.1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.menu-wrap {
  flex: 1;
  padding: 14px 0 10px;
  overflow: visible;
}

.sidebar-bottom {
  display: flex;
  justify-content: flex-start;
  padding: 6px 8px 4px;
}

:deep(.shell-menu) {
  border-right: none;
  background: transparent;
}

:deep(.shell-menu .el-menu-item) {
  height: 46px;
  margin: 4px 0;
  border-radius: 10px;
  color: #475467;
  padding-left: 12px !important;
  font-size: 15px;
  font-weight: 700;
}

:deep(.shell-menu .el-menu-item:hover) {
  background: #f4f7fd;
  color: var(--rsa-primary);
}

:deep(.shell-menu .el-menu-item.is-active) {
  color: var(--rsa-primary);
  background: var(--rsa-primary-soft);
  font-weight: 600;
}

:deep(.shell-menu .el-sub-menu__title) {
  height: 46px;
  border-radius: 10px;
  margin: 4px 0;
  color: #475467;
  padding-left: 12px !important;
  font-size: 15px;
  font-weight: 700;
}

:deep(.shell-menu .el-sub-menu__title:hover) {
  background: #f4f7fd;
  color: var(--rsa-primary);
}

:deep(.shell-menu .el-sub-menu.is-opened > .el-sub-menu__title) {
  color: var(--rsa-primary);
  background: var(--rsa-primary-soft);
  font-weight: 600;
}

:deep(.shell-menu .el-sub-menu .el-menu-item) {
  padding-left: 44px !important;
  font-weight: 700;
}

.menu-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  margin-right: 10px;
  flex: 0 0 20px;
}

.menu-icon :deep(svg) {
  display: block;
}

.icon-btn .menu-icon,
.logout-btn .menu-icon {
  margin-right: 0;
}

.main {
  flex: 1;
  background: var(--rsa-bg);
  min-width: 0;
  overflow: auto;
}

.main-inner {
  min-height: 100%;
  padding: 20px 24px;
  box-sizing: border-box;
}

.icon-btn {
  width: 36px;
  height: 36px;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
  color: #667085;
  background: #fff;
  padding: 0;
  margin: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logout-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #e5e7eb;
  color: #667085;
  background: #fff;
  border-radius: 6px;
  padding: 0;
  margin: 0;
}

.logout-btn:hover {
  background: #f8fafc;
  color: var(--rsa-primary);
}


.sidebar.collapsed :deep(.shell-menu .el-menu-item),
.sidebar.collapsed :deep(.shell-menu .el-sub-menu__title) {
  width: 36px;
  height: 36px;
  margin: 4px auto;
  padding: 0 !important;
  border: 0;
  border-radius: 8px;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  text-align: center;
  position: relative;
}

.sidebar.collapsed :deep(.shell-menu .el-menu-item:hover),
.sidebar.collapsed :deep(.shell-menu .el-sub-menu__title:hover) {
  background: #f4f7fd;
  color: var(--rsa-primary);
}

.sidebar.collapsed :deep(.shell-menu .el-menu-item .menu-icon),
.sidebar.collapsed :deep(.shell-menu .el-sub-menu__title .menu-icon) {
  margin: 0 !important;
  width: 18px;
  height: 18px;
  flex: 0 0 18px;
  position: static !important;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transform: translateX(var(--collapsed-axis-offset-x));
}

.sidebar.collapsed :deep(.shell-menu .el-menu-item .menu-icon svg),
.sidebar.collapsed :deep(.shell-menu .el-sub-menu__title .menu-icon svg) {
  width: 18px !important;
  height: 18px !important;
  display: block;
  margin: 0 auto;
}

.icon-btn .menu-icon,
.logout-btn .menu-icon {
  width: 18px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.icon-btn .menu-icon :deep(svg),
.logout-btn .menu-icon :deep(svg) {
  width: 18px;
  height: 18px;
  display: block;
  margin: 0 auto;
}

.sidebar.collapsed :deep(.shell-menu .el-menu-item.is-active),
.sidebar.collapsed :deep(.shell-menu .el-sub-menu.is-opened > .el-sub-menu__title) {
  background: var(--rsa-primary-soft);
  color: var(--rsa-primary);
  box-shadow: inset 0 0 0 1px #dde4ff;
}

.sidebar.collapsed :deep(.shell-menu .el-sub-menu .el-menu-item) {
  display: none;
}

.sidebar.collapsed :deep(.shell-menu .el-sub-menu .el-menu) {
  display: none;
}

.sidebar.collapsed :deep(.shell-menu .el-sub-menu__icon-arrow) {
  display: none;
}

.sidebar.collapsed :deep(.shell-menu .menu-label) {
  display: none !important;
}

/* 收起状态：全栏元素锁定同一中心线，防止图标漂移 */
.sidebar.collapsed .sidebar-top,
.sidebar.collapsed .sidebar-bottom {
  display: flex;
  justify-content: center;
  padding-left: 0;
  padding-right: 0;
}

.sidebar.collapsed .icon-btn,
.sidebar.collapsed .logout-btn {
  margin: 0 auto;
}

.sidebar.collapsed .menu-wrap {
  display: block;
}

.sidebar.collapsed .menu-wrap :deep(.el-scrollbar__view) {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.sidebar.collapsed .menu-wrap :deep(.el-menu) {
  width: 36px;
  min-width: 36px;
  margin: 0 auto;
}

</style>
