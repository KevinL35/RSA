import { createRouter, createWebHistory, type RouteLocationNormalized } from 'vue-router'
import { ElMessage } from 'element-plus'
import { i18n } from '../i18n'
import LoginPage from '../../modules/auth/pages/LoginPage.vue'
import MainLayout from '../layouts/MainLayout.vue'
import { pathRequiredMenuKey, firstAllowedPath } from '../../modules/auth/routeMenu'
import { isPlatformMenuAuth, useAuthStore } from '../../modules/auth/store/auth.store'
import InsightAnalysisPage from '../../modules/insight/pages/InsightAnalysisPage.vue'
import InsightResultPage from '../../modules/insight/pages/InsightResultPage.vue'
import CompareAnalysisPage from '../../modules/compare/pages/CompareAnalysisPage.vue'
import CompareResultPage from '../../modules/compare/pages/CompareResultPage.vue'
import PainAuditPage from '../../modules/governance/pages/PainAuditPage.vue'
import DictionaryPage from '../../modules/governance/pages/DictionaryPage.vue'
import ApiConfigPage from '../../modules/settings/pages/ApiConfigPage.vue'
import AuditLogPage from '../../modules/settings/pages/AuditLogPage.vue'
import AccountPermissionsPage from '../../modules/settings/pages/AccountPermissionsPage.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: LoginPage },
    {
      path: '/',
      component: MainLayout,
      children: [
        { path: '', redirect: '/insight-analysis' },
        { path: 'insight-analysis', component: InsightAnalysisPage },
        { path: 'insight-analysis/result/:taskId', component: InsightResultPage },
        { path: 'compare-analysis', component: CompareAnalysisPage },
        { path: 'compare-analysis/result/:compareId', component: CompareResultPage },
        { path: 'pain-mining', redirect: '/dictionary-review' },
        {
          path: 'dictionary-review',
          component: PainAuditPage,
          meta: { allowedRoles: ['admin'] },
        },
        { path: 'pain-audit', redirect: '/dictionary-review' },
        { path: 'dictionary', component: DictionaryPage, meta: { allowedRoles: ['admin'] } },
        { path: 'task-center', redirect: '/insight-analysis' },
        { path: 'system-settings/api-config', component: ApiConfigPage, meta: { allowedRoles: ['admin'] } },
        { path: 'system-settings/audit-log', component: AuditLogPage, meta: { allowedRoles: ['admin'] } },
        {
          path: 'system-settings/account-permissions',
          component: AccountPermissionsPage,
          meta: { allowedRoles: ['admin'] },
        },
        { path: ':pathMatch(.*)*', redirect: '/insight-analysis' },
      ],
    },
  ],
})

// TB-7：登录 + 路由级 RBAC；平台用户另按 menu_keys 约束路由
router.beforeEach((to: RouteLocationNormalized) => {
  const auth = useAuthStore()
  if (to.path === '/login') return true
  if (!auth.isLogin()) return { path: '/login', query: { redirect: to.fullPath } }

  if (isPlatformMenuAuth()) {
    const keys = auth.menuKeys.value
    const need = pathRequiredMenuKey(to.path)
    if (need && !keys.includes(need)) {
      ElMessage.warning(i18n.global.t('router.noPermission'))
      return { path: firstAllowedPath(keys), replace: true }
    }
    return true
  }

  const roles = to.meta.allowedRoles
  if (roles?.length && !roles.includes(auth.role.value)) {
    ElMessage.warning(i18n.global.t('router.noPermission'))
    return { path: '/insight-analysis', replace: true }
  }
  return true
})

export default router
