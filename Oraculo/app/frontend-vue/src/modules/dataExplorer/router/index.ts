import type { RouteRecordRaw } from 'vue-router'
import MainLayout from '@/common/components/layout/MainLayout.vue'

const dataExplorerRoutes: RouteRecordRaw[] = [
  {
    path: '/explorar',
    component: MainLayout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'ExplorarDados',
        component: () => import('@/modules/dataExplorer/views/ExplorarDadosView.vue')
      }
    ]
  },
  {
    path: '/admin/data-validation',
    component: MainLayout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'DataValidation',
        component: () => import('@/modules/dataExplorer/views/DataValidationView.vue')
      }
    ]
  }
]

export default dataExplorerRoutes
