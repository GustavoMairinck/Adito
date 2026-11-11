import type { RouteRecordRaw } from 'vue-router'
import MainLayout from '@/common/components/layout/MainLayout.vue'

const adminRoutes: RouteRecordRaw[] = [
  {
    path: '/admin',
    component: MainLayout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Admin',
        component: () => import('@/modules/admin/views/AdminView.vue')
      }
    ]
  }
]

export default adminRoutes
