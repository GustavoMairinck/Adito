import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuth } from '@/modules/auth/composables/useAuth'

// Module routes
import authRoutes from '@/modules/auth/router'
import dashboardRoutes from '@/modules/dashboard/router'
import chatRoutes from '@/modules/chat/router'
import dataExplorerRoutes from '@/modules/dataExplorer/router'
import adminRoutes from '@/modules/admin/router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/chat'
  },
  ...authRoutes,
  ...dashboardRoutes,
  ...chatRoutes,
  ...dataExplorerRoutes,
  ...adminRoutes,
  {
    path: '/:pathMatch(.*)*',
    redirect: '/chat'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Global Navigation Guard
router.beforeEach((to) => {
  const auth = useAuth()
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth !== false)
  const isLoginPage = to.name === 'Login'

  if (requiresAuth && !auth.isAuthenticated.value) {
    // Redirect non-authenticated users to login
    return { name: 'Login', query: { redirect: to.fullPath } }
  } else if (isLoginPage && auth.isAuthenticated.value) {
    // Redirect authenticated users away from login
    return { name: 'ChatEstrategico' }
  }
})

export default router