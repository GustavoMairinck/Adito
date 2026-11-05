import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import ui from '@nuxt/ui/vite'
import { fileURLToPath, URL } from 'node:url'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    ui()
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    // O app Tauri em modo dev carrega exatamente esta porta (src-tauri/tauri.conf.json → devUrl);
    // se ela estiver ocupada, falhar é melhor que subir noutra porta que o app não acha.
    port: 5173,
    strictPort: true,
    host: true,
    watch: {
      usePolling: true
    }
  }
})
