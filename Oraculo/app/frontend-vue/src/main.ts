import './style.css'

import { createApp } from 'vue'
import ui from '@nuxt/ui/vue-plugin'
import { MotionPlugin } from '@vueuse/motion'
import App from './App.vue'
import router from './common/router'
import { initBackend } from './common/api/config'
import { useAuth } from './modules/auth/composables/useAuth'

async function bootstrap() {
  // No desktop, espera o Tauri informar a porta e o token do backend local.
  await initBackend()
  try {
    await useAuth().loadLocalUser()
  } catch (err) {
    console.error('Backend local indisponível', err)
  }

  const app = createApp(App)
  app.use(router)
  app.use(ui)
  app.use(MotionPlugin)
  app.mount('#app')
}

bootstrap()
