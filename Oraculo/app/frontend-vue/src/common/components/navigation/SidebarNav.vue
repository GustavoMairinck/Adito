<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuth } from '@/modules/auth/composables/useAuth'
import { useRoute } from 'vue-router'
import brandIcon from '@/common/assets/brand-icon.png'
import {
  AreaChart,
  MessageSquare,
  Database,
  Settings,
  KeyRound,
  Sun,
  Moon,
  ShieldCheck,
  PanelLeftClose,
  PanelLeftOpen,
  X
} from 'lucide-vue-next'

const props = defineProps<{
  isOpen?: boolean
}>()

const emit = defineEmits(['update:isOpen'])

const { user } = useAuth()
const route = useRoute()

const isDark = ref(document.documentElement.classList.contains('dark'))
const isCollapsed = ref(false)
const isMobile = ref(false)

// Robust mobile detection via media query
onMounted(() => {
  if (typeof window !== 'undefined') {
    const mql = window.matchMedia('(max-width: 767px)')
    isMobile.value = mql.matches

    mql.addEventListener('change', (e) => {
      isMobile.value = e.matches
      if (!e.matches && props.isOpen) {
        // Close mobile sidebar state when moving to desktop
        emit('update:isOpen', false)
      }
    })
  }
})

// On mobile, we never want it collapsed. On desktop, follow user preference.
const isEffectivelyCollapsed = computed(() => isCollapsed.value && !isMobile.value)

function closeSidebar() {
  emit('update:isOpen', false)
}

const menuItems = [
  { icon: MessageSquare, label: 'Chat', path: '/chat' },
  { icon: AreaChart, label: 'Meu Dashboard', path: '/meu-dashboard' },
  { icon: Database, label: 'Explorar Dados', path: '/explorar' },
  { icon: ShieldCheck, label: 'Validacao de Dados', path: '/admin/data-validation', adminOnly: true },
  { icon: Settings, label: 'Administracao', path: '/admin', adminOnly: true },
  { icon: KeyRound, label: 'Configurações', path: '/configuracoes' }
]

const visibleMenuItems = computed(() =>
  menuItems.filter(item => !item.adminOnly || user.value?.role === 'admin')
)

const initials = computed(() => {
  if (!user.value?.username) return 'UN'
  return user.value.username
    .split(' ')
    .map((name: string) => name[0])
    .join('')
    .toUpperCase()
    .substring(0, 2)
})

function toggleTheme() {
  const next = isDark.value ? 'light' : 'dark'
  if (next === 'dark') {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
  localStorage.setItem('theme', next)
  isDark.value = next === 'dark'
}
</script>

<template>
  <aside
    :class="[
      'fixed left-0 top-0 z-[60] flex h-screen flex-col overflow-hidden border-r border-white/[0.07] bg-[#0f1923] text-[#e8edf5] shadow-[rgba(0,0,0,0.3)_0px_0px_0px_1px] transition-all duration-300 md:relative dark:bg-[#0d1117]',
      !isOpen ? '-translate-x-full md:translate-x-0' : 'translate-x-0',
      'w-64',
      isEffectivelyCollapsed ? 'md:w-20' : 'md:w-64'
    ]"
  >
    <div class="border-b border-white/10 px-5 py-6">
      <div :class="['flex items-center', isEffectivelyCollapsed ? 'flex-col gap-5 justify-center' : 'justify-between']">
        <div class="flex items-center gap-3">
          <img :src="brandIcon" alt="Logo" class="h-[34px] w-[34px] shrink-0 object-contain" />
          <div v-if="!isEffectivelyCollapsed" class="relative animate-in fade-in duration-300">
            <span class="absolute -top-[16px] left-0 flex items-center justify-center rounded-full border border-blue-400/50 bg-[#0f1923] px-[5px] py-[2px] text-[8px] font-bold uppercase tracking-[0.1em] text-blue-400/70 leading-none select-none whitespace-nowrap">
              beta
            </span>
            <h1 class="text-[18px] font-semibold tracking-[-0.04em] text-white">
              ORACULO-ESX
            </h1>
          </div>
        </div>

        <div class="flex items-center">
          <button
            v-if="!isMobile"
            :title="isCollapsed ? 'Expandir' : 'Recolher'"
            class="hidden rounded-lg border border-transparent p-2 text-white/45 transition-colors hover:bg-white/[0.04] hover:text-white/70 md:flex"
            @click="isCollapsed = !isCollapsed"
          >
            <PanelLeftOpen v-if="isCollapsed" class="h-5 w-5" />
            <PanelLeftClose v-else class="h-5 w-5" />
          </button>

          <button
            v-if="isMobile"
            class="rounded-lg bg-white/[0.04] p-2 text-white/60 transition-colors hover:bg-white/[0.08] md:hidden"
            @click="closeSidebar"
          >
            <X class="h-5 w-5" />
          </button>
        </div>
      </div>

      <div v-if="!isEffectivelyCollapsed" class="mt-2.5 animate-in fade-in slide-in-from-left-4 duration-500">
        <p class="text-[9px] font-bold uppercase tracking-[0.22em] text-white/35 whitespace-nowrap">
          Inteligência Estratégica
        </p>
      </div>
    </div>

    <nav :class="['no-scrollbar flex-1 overflow-y-auto py-6', isCollapsed ? 'px-2' : 'px-4']">
      <RouterLink
        v-for="item in visibleMenuItems"
        :key="item.path"
        :class="[
          'group relative mb-1.5 flex items-center gap-3 rounded-md border px-3.5 py-2.5 transition-all duration-150',
          route.path === item.path
            ? 'border-white/[0.09] bg-white/[0.07] text-white'
            : 'border-transparent text-white/55 hover:bg-white/[0.04] hover:text-white/90',
          isCollapsed ? 'justify-center px-0' : ''
        ]"
        :title="isCollapsed ? item.label : ''"
        :to="item.path"
        @click="closeSidebar"
      >
        <component
          :is="item.icon"
          :class="['h-5 w-5 transition-colors duration-150', route.path === item.path ? 'text-blue-400' : 'text-white/90 group-hover:text-white']"
        />
        <span
          v-if="!isEffectivelyCollapsed"
          :class="['flex-1 text-sm font-medium tracking-[0.005em]', route.path === item.path ? 'text-white' : 'text-white/70 group-hover:text-white/90']"
        >
          {{ item.label }}
        </span>
        <div
          v-if="route.path === item.path"
          class="absolute left-0 top-1/2 h-4 w-[3px] -translate-y-1/2 rounded-r-sm bg-blue-400"

        />
      </RouterLink>
    </nav>

    <div class="border-t border-white/10 bg-black/10 p-4">
      <div :class="['mb-5 flex items-center gap-3', isEffectivelyCollapsed ? 'justify-center' : '']">
        <div class="flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-full border border-white/10 bg-white/[0.08] text-sm font-medium text-[#f3ede4]">
          <span v-if="!user?.avatar">{{ initials }}</span>
          <img v-else :src="user.avatar" alt="Avatar" class="h-full w-full object-cover">
        </div>
        <div v-if="!isEffectivelyCollapsed" class="animate-in fade-in min-w-0 flex-1 duration-300">
          <p class="truncate text-sm font-medium text-white">{{ user?.name || user?.username || 'Usuario' }}</p>
          <p class="truncate text-[10px] font-medium tracking-[0.03em] text-white/50">{{ user?.email || 'gestor@ifes.edu.br' }}</p>
        </div>
      </div>

      <div class="space-y-2">

        <button
          :class="['flex w-full items-center gap-2.5 rounded-md border border-white/[0.07] bg-white/[0.03] text-[10px] font-medium uppercase tracking-[0.1em] text-white/55 transition-colors hover:bg-white/[0.06] hover:text-white/80', isEffectivelyCollapsed ? 'justify-center p-3' : 'px-4 py-2.5']"
          :title="isDark ? 'Modo Claro' : 'Modo Escuro'"
          @click="toggleTheme"
        >
          <Sun v-if="isDark" class="h-4 w-4 text-white/70" />
          <Moon v-else class="h-4 w-4 text-white/70" />
          <span v-if="!isEffectivelyCollapsed">{{ isDark ? 'Modo Claro' : 'Modo Escuro' }}</span>
        </button>
      </div>
    </div>

    <div v-if="!isEffectivelyCollapsed" class="bg-black/10 px-4 py-3 text-center text-[9px] font-medium uppercase tracking-[0.08em] text-white/20">
      FAPES • IFES • LEDS
    </div>
  </aside>
</template>

<style scoped>
.no-scrollbar::-webkit-scrollbar {
  display: none;
}

.no-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>