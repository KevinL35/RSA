import { createRouter, createWebHistory } from 'vue-router'
import LoginPage from '../../modules/auth/pages/LoginPage.vue'
import MainLayout from '../layouts/MainLayout.vue'
import InsightAnalysisPage from '../../modules/insight/pages/InsightAnalysisPage.vue'
import CompareAnalysisPage from '../../modules/compare/pages/CompareAnalysisPage.vue'
import PainAuditPage from '../../modules/governance/pages/PainAuditPage.vue'
import DictionaryPage from '../../modules/governance/pages/DictionaryPage.vue'
import TaskCenterPage from '../../modules/tasks/pages/TaskCenterPage.vue'
import ApiConfigPage from '../../modules/settings/pages/ApiConfigPage.vue'
import AccountPermissionsPage from '../../modules/settings/pages/AccountPermissionsPage.vue'
import { useAuthStore } from '../../modules/auth/store/auth.store'

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
        { path: 'compare-analysis', component: CompareAnalysisPage },
        { path: 'pain-audit', component: PainAuditPage },
        { path: 'dictionary', component: DictionaryPage },
        { path: 'task-center', component: TaskCenterPage },
        { path: 'system-settings/api-config', component: ApiConfigPage },
        { path: 'system-settings/account-permissions', component: AccountPermissionsPage },
      ],
    },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.path !== '/login' && !auth.isLogin()) return '/login'
  if (to.path === '/login' && auth.isLogin()) return '/insight-analysis'
  return true
})

export default router
