import type { RouteRecordRaw } from 'vue-router'
import MainLayout from '@/common/components/layout/MainLayout.vue'

const settingsRoutes: RouteRecordRaw[] = [
  {
    path: '/configuracoes',
    component: MainLayout,
    children: [
      {
        path: '',
        name: 'Configuracoes',
        component: () => import('@/modules/settings/views/ConfiguracoesView.vue')
      }
    ]
  }
]

export default settingsRoutes
