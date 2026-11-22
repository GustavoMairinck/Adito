<script setup lang="ts">
import { ref } from 'vue'
import SidebarNav from '@/common/components/navigation/SidebarNav.vue'
import { Menu } from 'lucide-vue-next'

import BrandIcon from '@/common/components/BrandIcon.vue'

const isSidebarOpen = ref(false)

function toggleSidebar() {
  isSidebarOpen.value = !isSidebarOpen.value
}
</script>

<template>
  <div class="flex h-screen overflow-hidden bg-primary text-primary">
    <header class="md:hidden fixed top-0 left-0 right-0 z-50 flex h-16 items-center justify-between border-b border-border-subtle bg-surface/95 px-5 backdrop-blur-md">
      <div class="flex items-center gap-2">
        <BrandIcon class="h-8 w-8" />
        <h1 class="text-xl font-semibold tracking-[-0.04em] text-primary">Adito</h1>
      </div>

      <button
        aria-label="Abrir menu de navegação"
        :aria-expanded="isSidebarOpen"
        @click="toggleSidebar"
        class="rounded-lg border border-border-subtle bg-surface-elevated/90 p-2.5 text-text-secondary transition-colors hover:bg-surface-elevated hover:text-primary"
      >
        <Menu class="h-6 w-6" />
      </button>
    </header>

    <SidebarNav v-model:isOpen="isSidebarOpen" />

    <main class="min-w-0 flex-1 overflow-y-auto pt-16 md:pt-0">
      <RouterView />
    </main>

    <div
      v-if="isSidebarOpen"
      class="md:hidden fixed inset-0 z-[55] bg-black/45 backdrop-blur-sm transition-opacity duration-300"
      @click="isSidebarOpen = false"
    />
  </div>
</template>
