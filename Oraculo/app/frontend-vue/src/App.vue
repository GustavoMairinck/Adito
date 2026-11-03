<script setup lang="ts">
import { onMounted } from 'vue'

/**
 * App.vue — Componente raiz.
 * Envolve toda a aplicação com UApp (Nuxt UI) e RouterView.
 */

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
})
</script>

<template>
  <UApp>
    <RouterView />
  </UApp>
</template>
