import { createRouter, createWebHistory, type RouteLocationNormalized } from 'vue-router'
import { ElMessage } from 'element-plus'
import { i18n } from '../i18n'
import LoginPage from '../../modules/auth/pages/LoginPage.vue'
import MainLayout from '../layouts/MainLayout.vue'
import { pathRequiredMenuKey, firstAllowedPath } from '../../modules/auth/routeMenu'
import { isPlatformMenuAuth, useAuthStore } from '../../modules/auth/store/auth.store'
import InsightAnalysisPage from '../../modules/insight/pages/InsightAnalysisPage.vue'
import InsightResultPage from '../../modules/insight/pages/InsightResultPage.vue'
import SmartMiningPage from '../../modules/governance/pages/SmartMiningPage.vue'
import DictionaryPage from '../../modules/governance/pages/DictionaryPage.vue'
import ApiConfigPage from '../../modules/settings/pages/ApiConfigPage.vue'
import AuditLogPage from '../../modules/settings/pages/AuditLogPage.vue'

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
        { path: 'compare-analysis', redirect: '/insight-analysis' },
        { path: 'compare-analysis/result/:compareId', redirect: '/insight-analysis' },
        { path: 'pain-mining', redirect: '/smart-mining' },
        {
          path: 'smart-mining',
          component: SmartMiningPage,
          meta: { allowedRoles: ['admin'] },
        },
        { path: 'dictionary-review', redirect: '/smart-mining' },
        { path: 'dictionary', component: DictionaryPage, meta: { allowedRoles: ['admin'] } },
        { path: 'task-center', redirect: '/insight-analysis' },
        { path: 'system-settings/audit-log', component: AuditLogPage, meta: { allowedRoles: ['admin'] } },
        { path: 'system-settings/api-config', component: ApiConfigPage, meta: { allowedRoles: ['admin'] } },
        { path: ':pathMatch(.*)*', redirect: '/insight-analysis' },
      ],
    },
  ],
})


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
