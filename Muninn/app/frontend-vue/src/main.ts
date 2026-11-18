import './style.css'

import { createApp } from 'vue'
import ui from '@nuxt/ui/vue-plugin'
import { MotionPlugin } from '@vueuse/motion'
import App from './App.vue'
import router from './common/router'
import { coreReady } from './common/api/core'
import { useAuth } from './modules/auth/composables/useAuth'

/** Sem o núcleo não há o que mostrar: em vez da tela branca, diz o motivo (com o caminho do log). */
function showFatal(message: string) {
  const root = document.getElementById('app')
  if (!root) return
  root.innerHTML = ''
  const box = document.createElement('div')
  box.style.cssText = 'max-width:640px;margin:15vh auto;padding:24px;font-family:sans-serif;line-height:1.5'
  const title = document.createElement('h1')
  title.textContent = 'O Muninn não conseguiu iniciar'
  title.style.cssText = 'font-size:20px;margin:0 0 12px'
  const text = document.createElement('p')
  text.textContent = message
  text.style.cssText = 'white-space:pre-wrap;margin:0'
  box.append(title, text)
  root.append(box)
}

async function bootstrap() {
  // Espera o núcleo local (Python) ficar pronto.
  try {
    await coreReady()
  } catch (err) {
    showFatal(String(err))
    return
  }
  try {
    await useAuth().loadLocalUser()
  } catch (err) {
    console.error('Núcleo local indisponível', err)
  }

  const app = createApp(App)
  app.use(router)
  app.use(ui)
  app.use(MotionPlugin)
  app.mount('#app')
}

bootstrap()
