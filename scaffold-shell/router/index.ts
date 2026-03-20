import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/LoginView.vue'
import MainLayout from '../layouts/MainLayout.vue'
import DashboardView from '../views/DashboardView.vue'
import PlaceholderView from '../views/PlaceholderView.vue'
import ApiConfigView from '../views/ApiConfigView.vue'
import AccountPermissionsView from '../views/AccountPermissionsView.vue'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: LoginView },
    {
      path: '/',
      component: MainLayout,
      children: [
        { path: '', redirect: '/insight-analysis' },
        { path: 'insight-analysis', component: DashboardView },
        { path: 'compare-analysis', component: PlaceholderView },
        { path: 'pain-audit', component: PlaceholderView },
        { path: 'dictionary', component: PlaceholderView },
        { path: 'task-center', component: PlaceholderView },
        { path: 'system-settings/api-config', component: ApiConfigView },
        { path: 'system-settings/account-permissions', component: AccountPermissionsView },
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
