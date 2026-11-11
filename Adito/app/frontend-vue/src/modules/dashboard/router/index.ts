import type { RouteRecordRaw } from 'vue-router'
import MainLayout from '@/common/components/layout/MainLayout.vue'

const dashboardRoutes: RouteRecordRaw[] = [
  {
    path: '/dashboard',
    component: MainLayout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('@/modules/dashboard/views/DashboardView.vue')
      }
    ]
  },
  {
    path: '/meu-dashboard',
    component: MainLayout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'MeuDashboard',
        component: () => import('@/modules/dashboard/views/MeuDashboardView.vue')
      }
    ]
  }
]

export default dashboardRoutes
