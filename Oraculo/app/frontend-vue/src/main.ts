import './style.css'

import { createApp } from 'vue'
import ui from '@nuxt/ui/vue-plugin'
import { MotionPlugin } from '@vueuse/motion'
import App from './App.vue'
import router from './common/router'

const app = createApp(App)

app.use(router)
app.use(ui)
app.use(MotionPlugin)

app.mount('#app')
