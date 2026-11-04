import type { RouteRecordRaw } from 'vue-router'
import MainLayout from '@/common/components/layout/MainLayout.vue'

const chatRoutes: RouteRecordRaw[] = [
  {
    path: '/chat',
    component: MainLayout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'ChatEstrategico',
        component: () => import('@/modules/chat/views/ChatEstrategicoView.vue')
      }
    ]
  }
]

export default chatRoutes
