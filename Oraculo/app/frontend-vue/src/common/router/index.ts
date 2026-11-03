import { createRouter, createWebHashHistory, type RouteRecordRaw } from 'vue-router'

// Module routes
import dashboardRoutes from '@/modules/dashboard/router'
import chatRoutes from '@/modules/chat/router'
import dataExplorerRoutes from '@/modules/dataExplorer/router'
import adminRoutes from '@/modules/admin/router'

// Desktop sem login: não há rota /login nem guarda de autenticação.
const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/chat'
  },
  ...dashboardRoutes,
  ...chatRoutes,
  ...dataExplorerRoutes,
  ...adminRoutes,
  {
    path: '/:pathMatch(.*)*',
    redirect: '/chat'
  }
]

// Hash history: o webview do Tauri serve arquivos estáticos, sem fallback para rotas profundas.
const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export default router
