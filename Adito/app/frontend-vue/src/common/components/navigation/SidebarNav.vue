<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuth } from '@/modules/auth/composables/useAuth'
import { useRoute } from 'vue-router'
import BrandIcon from '@/common/components/BrandIcon.vue'
import {
  AreaChart,
  Database,
  MessageSquare,
  Settings,
  KeyRound,
  Sun,
  Moon,
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
  { icon: AreaChart, label: 'Meu painel', path: '/meu-dashboard' },
  { icon: Database, label: 'Explorar dados', path: '/explorar' },
  { icon: Settings, label: 'Administração', path: '/admin', adminOnly: true },
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
      'fixed left-0 top-0 z-[60] flex h-screen flex-col overflow-hidden border-r border-white/[0.08] bg-[var(--brand-dark)] text-white shadow-[rgba(0,0,0,0.3)_0px_0px_0px_1px] transition-all duration-300 md:relative',
      !isOpen ? '-translate-x-full md:translate-x-0' : 'translate-x-0',
      'w-64',
      isEffectivelyCollapsed ? 'md:w-20' : 'md:w-64'
    ]"
  >
    <div class="border-b border-white/10 px-5 py-6">
      <div :class="['flex items-center', isEffectivelyCollapsed ? 'flex-col gap-5 justify-center' : 'justify-between']">
        <div class="flex items-center gap-2">
          <BrandIcon class="h-[34px] w-[34px]" />
          <div v-if="!isEffectivelyCollapsed" class="relative animate-in fade-in duration-300">
            <h1 class="adito-wordmark text-[26px] leading-none text-white">
              Adito
            </h1>
          </div>
        </div>

        <div class="flex items-center">
          <button
            v-if="!isMobile"
            :title="isCollapsed ? 'Expandir' : 'Recolher'"
            class="hidden rounded-lg border border-transparent p-2 text-white/60 transition-colors hover:bg-white/[0.08] hover:text-white md:flex"
            @click="isCollapsed = !isCollapsed"
          >
            <PanelLeftOpen v-if="isCollapsed" class="h-5 w-5" />
            <PanelLeftClose v-else class="h-5 w-5" />
          </button>

          <button
            v-if="isMobile"
            aria-label="Fechar menu de navegação"
            class="rounded-lg bg-white/[0.06] p-2 text-white/75 transition-colors hover:bg-white/[0.12] md:hidden"
            @click="closeSidebar"
          >
            <X class="h-5 w-5" />
          </button>
        </div>
      </div>

      <div v-if="!isEffectivelyCollapsed" class="mt-2.5 animate-in fade-in slide-in-from-left-4 duration-500">
        <p class="text-[11px] font-medium tracking-[0.04em] text-white/60 whitespace-nowrap">
          Pesquisa e extensão
        </p>
      </div>
    </div>

    <nav aria-label="Navegação principal" :class="['no-scrollbar flex-1 overflow-y-auto py-6', isCollapsed ? 'px-2' : 'px-4']">
      <RouterLink
        v-for="item in visibleMenuItems"
        :key="item.path"
        :class="[
          'group relative mb-1.5 flex items-center gap-3 rounded-lg border px-3.5 py-2.5 transition-all duration-150',
          route.path === item.path
            ? 'border-white/[0.12] bg-white/[0.12] text-white dark:border-[rgba(54,146,81,0.28)] dark:bg-[rgba(43,122,66,0.25)]'
            : 'border-transparent text-white/75 hover:bg-white/[0.06] hover:text-white',
          isCollapsed ? 'justify-center px-0' : ''
        ]"
        :title="isCollapsed ? item.label : ''"
        :to="item.path"
        @click="closeSidebar"
      >
        <span
          v-if="route.path === item.path"
          class="h-4 w-[3px] shrink-0 rounded-full bg-white/90 dark:bg-[#68d388]"
        />
        <component
          :is="item.icon"
          :class="[
            'h-5 w-5 shrink-0 transition-colors duration-150',
            route.path === item.path
              ? 'text-white dark:text-[#68d388]'
              : 'text-white/80 group-hover:text-white'
          ]"
        />
        <span
          v-if="!isEffectivelyCollapsed"
          :class="[
            'flex-1 text-sm tracking-[0.005em]',
            route.path === item.path
              ? 'font-semibold text-white'
              : 'font-medium text-white/80 group-hover:text-white'
          ]"
        >
          {{ item.label }}
        </span>
      </RouterLink>
    </nav>

    <div class="border-t border-white/10 bg-black/15 p-4">
      <div :class="['mb-5 flex items-center gap-3', isEffectivelyCollapsed ? 'justify-center' : '']">
        <div class="flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-full border border-white/15 bg-[var(--brand-primary)] text-sm font-semibold text-white">
          <span v-if="!user?.avatar">{{ initials }}</span>
          <img v-else :src="user.avatar" alt="Avatar" class="h-full w-full object-cover">
        </div>
        <div v-if="!isEffectivelyCollapsed" class="animate-in fade-in min-w-0 flex-1 duration-300">
          <p class="truncate text-sm font-medium text-white">{{ user?.name || user?.username || 'Usuário local' }}</p>
          <p class="truncate text-[10px] font-medium tracking-[0.03em] text-white/65">{{ user?.email || 'Consulta local de dados' }}</p>
        </div>
      </div>

      <div class="space-y-2">

        <button
          :class="['flex w-full items-center gap-2.5 rounded-md border border-white/[0.12] bg-white/[0.06] text-[10px] font-medium uppercase tracking-[0.1em] text-white/80 transition-colors hover:bg-white/[0.12] hover:text-white', isEffectivelyCollapsed ? 'justify-center p-3' : 'px-4 py-2.5']"
          :title="isDark ? 'Modo Claro' : 'Modo Escuro'"
          @click="toggleTheme"
        >
          <Sun v-if="isDark" class="h-4 w-4 text-white/85" />
          <Moon v-else class="h-4 w-4 text-white/85" />
          <span v-if="!isEffectivelyCollapsed">{{ isDark ? 'Modo Claro' : 'Modo Escuro' }}</span>
        </button>
      </div>
    </div>

    <div v-if="!isEffectivelyCollapsed" class="border-t border-white/[0.06] bg-black/20 px-4 py-3 text-center text-[9px] font-semibold uppercase tracking-[0.1em] text-white/65">
      IFES · Campus Serra
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
