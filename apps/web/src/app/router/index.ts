import { createRouter, createWebHistory, type RouteLocationNormalized } from 'vue-router'
import { ElMessage } from 'element-plus'
import { i18n } from '../i18n'
import LoginPage from '../../modules/auth/pages/LoginPage.vue'
import MainLayout from '../layouts/MainLayout.vue'
import { useAuthStore } from '../../modules/auth/store/auth.store'
import InsightAnalysisPage from '../../modules/insight/pages/InsightAnalysisPage.vue'
import InsightResultPage from '../../modules/insight/pages/InsightResultPage.vue'
import CompareAnalysisPage from '../../modules/compare/pages/CompareAnalysisPage.vue'
import CompareResultPage from '../../modules/compare/pages/CompareResultPage.vue'
import PainAuditPage from '../../modules/governance/pages/PainAuditPage.vue'
import DictionaryPage from '../../modules/governance/pages/DictionaryPage.vue'
import TaskCenterPage from '../../modules/tasks/pages/TaskCenterPage.vue'
import ApiConfigPage from '../../modules/settings/pages/ApiConfigPage.vue'
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
        { path: 'pain-audit', component: PainAuditPage, meta: { allowedRoles: ['admin'] } },
        { path: 'dictionary', component: DictionaryPage, meta: { allowedRoles: ['admin'] } },
        { path: 'task-center', component: TaskCenterPage },
        { path: 'system-settings/api-config', component: ApiConfigPage, meta: { allowedRoles: ['admin'] } },
        {
          path: 'system-settings/account-permissions',
          component: AccountPermissionsPage,
          meta: { allowedRoles: ['admin'] },
        },
      ],
    },
  ],
})

// TB-7：登录 + 路由级 RBAC（与侧边栏 allowedRoles 一致）
router.beforeEach((to: RouteLocationNormalized) => {
  const auth = useAuthStore()
  if (to.path === '/login') return true
  if (!auth.isLogin()) return { path: '/login', query: { redirect: to.fullPath } }
  const roles = to.meta.allowedRoles
  if (roles?.length && !roles.includes(auth.role.value)) {
    ElMessage.warning(i18n.global.t('router.noPermission'))
    return { path: '/insight-analysis', replace: true }
  }
  return true
})

export default router
