<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'

/**
 * App.vue — Componente raiz.
 * Envolve toda a aplicação com UApp (Nuxt UI) e RouterView.
 */

let themeObserver: MutationObserver | null = null

function initializeTheme() {
  const saved = localStorage.getItem('theme')
  if (saved === 'dark') {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
}

onMounted(() => {
  initializeTheme()

  const favicon = document.querySelector<HTMLLinkElement>('link[rel="icon"]')
  if (favicon) {
    const syncFavicon = () => {
      const theme = document.documentElement.classList.contains('dark') ? 'dark' : 'light'
      favicon.href = `/brand/adito-${theme}.png`
    }
    syncFavicon()
    themeObserver = new MutationObserver(syncFavicon)
    themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
  }
})

onBeforeUnmount(() => {
  themeObserver?.disconnect()
})
</script>

<template>
  <UApp>
    <RouterView />
  </UApp>
</template>
