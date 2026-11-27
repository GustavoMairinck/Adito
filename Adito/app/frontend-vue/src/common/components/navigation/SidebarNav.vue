<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  AlertCircle,
  AreaChart,
  Check,
  CheckCircle2,
  Database,
  KeyRound,
  Loader2,
  MessageSquare,
  Moon,
  PanelLeftClose,
  PanelLeftOpen,
  Pencil,
  Pin,
  PinOff,
  Plus,
  Search,
  Settings,
  Sun,
  Trash2,
  X,
} from 'lucide-vue-next'
import BrandIcon from '@/common/components/BrandIcon.vue'
import ConfirmModal from '@/common/components/feedback/ConfirmModal.vue'
import AtualizacaoDisponivel from '@/common/components/navigation/AtualizacaoDisponivel.vue'
import { useToast } from '@/common/composables/useToast'
import { useAuth } from '@/modules/auth/composables/useAuth'
import { useChatApi } from '@/modules/chat/composables/useChatApi'
import { useChatHistory } from '@/modules/chat/composables/useChatHistory'
import type { Conversation } from '@/modules/chat/types'
import {
  formatConversationDate,
  groupConversations,
} from '@/modules/chat/utils/historyGroups'

const props = defineProps<{
  isOpen?: boolean
}>()

const emit = defineEmits(['update:isOpen'])

const { user } = useAuth()
const route = useRoute()
const router = useRouter()
const { toast, showToast } = useToast()

const {
  conversations,
  currentConvId,
  setCurrentConvId,
  handleNewConversation,
  handleDeleteConversation,
  handleRenameConversation,
  handleTogglePinConversation,
} = useChatHistory()

const { activeConversationIds } = useChatApi()

const isDark = ref(
  typeof document !== 'undefined' &&
    (document.documentElement.classList.contains('dark') ||
      (typeof localStorage !== 'undefined' && localStorage.getItem('theme') === 'dark')),
)
let themeObserver: MutationObserver | null = null
const isCollapsed = ref(false)
const isMobile = ref(false)

const isSearchOpen = ref(false)
const searchQuery = ref('')
const searchInputRef = ref<HTMLInputElement | null>(null)

const editingId = ref<string | null>(null)
const editingTitle = ref('')
const editInputRef = ref<HTMLInputElement | null>(null)

const conversationToDelete = ref<{ id: string; title: string } | null>(null)
const sidebarError = ref<string | null>(null)

let mediaQueryList: MediaQueryList | null = null
const handleMediaChange = (e: MediaQueryListEvent) => {
  isMobile.value = e.matches
  if (!e.matches && props.isOpen) {
    emit('update:isOpen', false)
  }
}

function handleGlobalShortcut(event: KeyboardEvent) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
    if (document.querySelector('[data-testid="primeiro-uso-dados"]')) return
    event.preventDefault()
    if (isCollapsed.value && !isMobile.value) {
      isCollapsed.value = false
    }
    isSearchOpen.value = true
    nextTick(() => searchInputRef.value?.focus())
    return
  }
  if (event.key === 'Escape' && isSearchOpen.value) {
    event.preventDefault()
    event.stopPropagation()
    event.stopImmediatePropagation()
    closeSearch()
  }
}

onMounted(() => {
  if (typeof window !== 'undefined') {
    mediaQueryList = window.matchMedia('(max-width: 767px)')
    isMobile.value = mediaQueryList.matches
    mediaQueryList.addEventListener('change', handleMediaChange)
    window.addEventListener('keydown', handleGlobalShortcut, true)
  }

  if (typeof document !== 'undefined') {
    const syncDark = () => {
      isDark.value = document.documentElement.classList.contains('dark')
    }
    syncDark()
    themeObserver = new MutationObserver(syncDark)
    themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
  }
})

onBeforeUnmount(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener('keydown', handleGlobalShortcut, true)
  }
  mediaQueryList?.removeEventListener('change', handleMediaChange)
  mediaQueryList = null
  themeObserver?.disconnect()
})

const isEffectivelyCollapsed = computed(() => isCollapsed.value && !isMobile.value)

function closeSidebar() {
  emit('update:isOpen', false)
}

function toggleSearch() {
  if (isSearchOpen.value) {
    closeSearch()
    return
  }
  if (isCollapsed.value && !isMobile.value) {
    isCollapsed.value = false
  }
  isSearchOpen.value = true
  nextTick(() => searchInputRef.value?.focus())
}

function closeSearch() {
  isSearchOpen.value = false
  searchQuery.value = ''
}

const menuItems = [
  { icon: MessageSquare, label: 'Chat', path: '/chat' },
  { icon: AreaChart, label: 'Meu painel', path: '/meu-dashboard' },
  { icon: Database, label: 'Explorar dados', path: '/explorar' },
  { icon: Settings, label: 'Administração', path: '/admin', adminOnly: true },
  { icon: KeyRound, label: 'Configurações', path: '/configuracoes' },
]

const visibleMenuItems = computed(() =>
  menuItems.filter((item) => !item.adminOnly || user.value?.role === 'admin'),
)

const normalizedQuery = computed(() => searchQuery.value.trim().toLowerCase())

interface SearchMatch {
  conversation: Conversation
  snippet: string | null
}

const searchResults = computed<SearchMatch[]>(() => {
  const q = normalizedQuery.value
  if (!q) return []
  const matches: SearchMatch[] = []
  for (const conv of conversations.value) {
    const titleHit = conv.title.toLowerCase().includes(q)
    const matchingMsg = conv.messages.find((m) => {
      if (m.id === 'welcome') return false
      const searchable = `${m.text || ''} ${m.report?.title || ''}`.toLowerCase()
      return searchable.includes(q)
    })
    if (!titleHit && !matchingMsg) continue
    let snippet: string | null = null
    const rawContent = matchingMsg?.text || matchingMsg?.report?.title || ''
    if (rawContent) {
      const text = rawContent.replace(/\s+/g, ' ').trim()
      const pos = text.toLowerCase().indexOf(q)
      if (pos >= 0) {
        const start = Math.max(0, pos - 24)
        const end = Math.min(text.length, pos + q.length + 40)
        snippet = `${start > 0 ? '…' : ''}${text.slice(start, end)}${end < text.length ? '…' : ''}`
      }
    }
    matches.push({ conversation: conv, snippet })
  }
  return matches
})

const groupedConversations = computed(() => groupConversations(conversations.value))

function startNewChat() {
  handleNewConversation()
  if (route.path !== '/chat') {
    router.push('/chat')
  }
  closeSidebar()
}

function selectConversation(id: string) {
  if (editingId.value === id) return
  setCurrentConvId(id)
  if (route.path !== '/chat') {
    router.push('/chat')
  }
  closeSidebar()
}

function startRename(conv: Conversation) {
  sidebarError.value = null
  editingId.value = conv.id
  editingTitle.value = conv.title
  nextTick(() => {
    const input = Array.isArray(editInputRef.value) ? editInputRef.value[0] : editInputRef.value
    input?.focus()
    input?.select()
  })
}

function cancelRename() {
  editingId.value = null
  editingTitle.value = ''
}

async function saveRename(id: string) {
  if (editingId.value !== id) return
  const next = editingTitle.value.trim()
  const currentTitle = conversations.value.find((c) => c.id === id)?.title
  cancelRename()
  if (!next || next === currentTitle) return
  try {
    sidebarError.value = null
    await handleRenameConversation(id, next)
    showToast('Conversa renomeada.', 'success')
  } catch (error: any) {
    const detail = error?.response?.data?.detail || error?.message || 'Não foi possível renomear a conversa.'
    sidebarError.value = detail
    showToast(detail, 'error')
  }
}

async function togglePin(conv: Conversation) {
  try {
    sidebarError.value = null
    const willPin = !conv.isPinned
    await handleTogglePinConversation(conv.id)
    showToast(willPin ? 'Conversa fixada.' : 'Conversa desafixada.', 'success')
  } catch (error: any) {
    const detail = error?.response?.data?.detail || error?.message || 'Não foi possível atualizar a fixação.'
    sidebarError.value = detail
    showToast(detail, 'error')
  }
}

function requestDelete(conv: Conversation) {
  conversationToDelete.value = { id: conv.id, title: conv.title }
}

async function confirmDelete() {
  if (!conversationToDelete.value) return
  try {
    sidebarError.value = null
    await handleDeleteConversation(conversationToDelete.value.id)
    conversationToDelete.value = null
    showToast('Conversa excluída com sucesso.', 'success')
  } catch (error: any) {
    const detail = error?.response?.data?.detail || error?.message || 'Erro ao excluir conversa.'
    sidebarError.value = detail
    showToast(detail, 'error')
  }
}

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
      'adito-sidebar fixed left-0 top-0 z-[60] flex h-screen flex-col overflow-hidden border-r border-white/[0.08] bg-[var(--brand-dark)] text-white shadow-[rgba(0,0,0,0.3)_0px_0px_0px_1px] transition-all duration-300 md:relative',
      !isOpen ? '-translate-x-full md:translate-x-0' : 'translate-x-0',
      isEffectivelyCollapsed ? 'adito-sidebar--collapsed md:w-20' : 'adito-sidebar--expanded',
    ]"
    data-testid="sidebar-nav"
  >
    <ConfirmModal
      :is-open="!!conversationToDelete"
      title="Excluir conversa"
      :message="conversationToDelete ? `Tem certeza que deseja excluir a conversa '${conversationToDelete.title}'?` : ''"
      confirm-text="Excluir conversa"
      cancel-text="Cancelar"
      @confirm="confirmDelete"
      @close="conversationToDelete = null"
    />

    <Teleport to="body">
      <transition
        enter-active-class="transition duration-200 ease-out"
        enter-from-class="opacity-0 translate-y-2"
        enter-to-class="opacity-100 translate-y-0"
        leave-active-class="transition duration-150 ease-in"
        leave-from-class="opacity-100 translate-y-0"
        leave-to-class="opacity-0 translate-y-2"
      >
        <div
          v-if="toast"
          role="status"
          :class="[
            'fixed right-4 bottom-4 z-[80] max-w-sm rounded-2xl px-4 py-3 shadow-2xl border flex items-start gap-3',
            toast.type === 'success'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-800 dark:bg-emerald-950/90 dark:border-emerald-500/30 dark:text-emerald-200'
              : 'bg-red-50 border-red-200 text-red-800 dark:bg-red-950/90 dark:border-red-500/30 dark:text-red-200',
          ]"
        >
          <CheckCircle2 v-if="toast.type === 'success'" class="h-5 w-5 mt-0.5 shrink-0" />
          <AlertCircle v-else class="h-5 w-5 mt-0.5 shrink-0" />
          <span class="text-sm font-medium">{{ toast.message }}</span>
        </div>
      </transition>
    </Teleport>

    <!-- Cabeçalho -->
    <div class="border-b border-white/10 px-4 py-4">
      <div :class="['flex items-center', isEffectivelyCollapsed ? 'flex-col gap-4 justify-center' : 'justify-between']">
        <div class="flex items-center gap-2.5">
          <BrandIcon class="h-[34px] w-[34px]" />
          <div v-if="!isEffectivelyCollapsed" class="relative animate-in fade-in duration-300">
            <h1 class="adito-wordmark text-[26px] leading-none text-white">
              Adito
            </h1>
          </div>
        </div>

        <div class="flex items-center gap-1">
          <button
            v-if="!isEffectivelyCollapsed"
            type="button"
            :class="['icon-button rounded-lg p-1.5 text-white/70 transition-colors hover:bg-white/[0.1] hover:text-white', { 'icon-button--active': isSearchOpen }]"
            :aria-expanded="isSearchOpen"
            aria-label="Buscar conversas"
            title="Buscar conversas (Ctrl+K)"
            @click="toggleSearch"
          >
            <Search class="h-4 w-4" />
          </button>

          <button
            v-if="!isMobile"
            type="button"
            :title="isCollapsed ? 'Expandir' : 'Recolher'"
            :aria-label="isCollapsed ? 'Expandir barra lateral' : 'Recolher barra lateral'"
            class="hidden rounded-lg border border-transparent p-1.5 text-white/65 transition-colors hover:bg-white/[0.1] hover:text-white md:flex"
            @click="isCollapsed = !isCollapsed"
          >
            <PanelLeftOpen v-if="isCollapsed" class="h-4.5 w-4.5" />
            <PanelLeftClose v-else class="h-4.5 w-4.5" />
          </button>

          <button
            v-if="isMobile"
            type="button"
            aria-label="Fechar menu de navegação"
            class="rounded-lg bg-white/[0.08] p-1.5 text-white/80 transition-colors hover:bg-white/[0.14] md:hidden"
            @click="closeSidebar"
          >
            <X class="h-4.5 w-4.5" />
          </button>
        </div>
      </div>

      <p
        v-if="!isEffectivelyCollapsed"
        class="mt-1.5 text-[12.5px] font-medium tracking-[0.03em] text-white/65 whitespace-nowrap"
      >
        Pesquisa e extensão
      </p>

      <!-- Busca expansível -->
      <div v-if="!isEffectivelyCollapsed && isSearchOpen" class="mt-3">
        <div class="relative">
          <Search class="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-white/55" />
          <input
            ref="searchInputRef"
            v-model="searchQuery"
            type="text"
            aria-label="Filtrar conversas"
            placeholder="Buscar nas conversas..."
            class="w-full rounded-lg border border-white/15 bg-white/[0.08] py-2 pl-9 pr-8 text-sm text-white placeholder:text-white/50 focus:border-white/35 focus:bg-white/[0.12] focus:outline-none"
          />
          <button
            v-if="searchQuery"
            type="button"
            aria-label="Limpar busca"
            class="absolute right-2 top-1/2 -translate-y-1/2 rounded p-0.5 text-white/60 hover:text-white"
            @click="searchQuery = ''"
          >
            <X class="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>

    <!-- Navegação + Novo Chat -->
    <nav aria-label="Navegação principal" :class="['border-b border-white/10 py-3', isEffectivelyCollapsed ? 'px-2' : 'px-3']">
      <RouterLink
        v-for="item in visibleMenuItems"
        :key="item.path"
        :class="[
          'group relative mb-1 flex items-center gap-3 rounded-lg border px-3 py-2.5 transition-all duration-150',
          route.path === item.path
            ? 'border-white/[0.14] bg-white/[0.12] text-white dark:border-[rgba(54,146,81,0.3)] dark:bg-[rgba(43,122,66,0.25)]'
            : 'border-transparent text-white/80 hover:bg-white/[0.07] hover:text-white',
          isEffectivelyCollapsed ? 'justify-center px-0' : '',
        ]"
        :title="isEffectivelyCollapsed ? item.label : ''"
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
            'h-[18px] w-[18px] shrink-0 transition-colors duration-150',
            route.path === item.path
              ? 'text-white dark:text-[#68d388]'
              : 'text-white/80 group-hover:text-white',
          ]"
        />
        <span
          v-if="!isEffectivelyCollapsed"
          :class="[
            'flex-1 text-[15px] tracking-[0.005em]',
            route.path === item.path
              ? 'font-semibold text-white'
              : 'font-medium text-white/85 group-hover:text-white',
          ]"
        >
          {{ item.label }}
        </span>
      </RouterLink>

      <button
        type="button"
        :class="[
          'mt-2 flex w-full items-center gap-2.5 rounded-lg border border-white/15 bg-white/[0.08] py-2.5 text-sm font-semibold text-white transition-colors hover:bg-white/[0.15]',
          isEffectivelyCollapsed ? 'justify-center px-0' : 'px-3',
        ]"
        :title="isEffectivelyCollapsed ? 'Novo chat' : ''"
        @click="startNewChat"
      >
        <Plus class="h-4.5 w-4.5 shrink-0" />
        <span v-if="!isEffectivelyCollapsed">Novo chat</span>
      </button>
    </nav>

    <!-- Conversas -->
    <div v-if="!isEffectivelyCollapsed" class="no-scrollbar flex-1 overflow-y-auto px-3 py-3">
      <div class="mb-2.5 flex items-center justify-between px-1">
        <span class="text-[13px] font-semibold uppercase tracking-[0.08em] text-white/70">
          Conversas
        </span>
        <span class="text-[13px] font-medium tabular-nums text-white/60">
          {{ conversations.length }}
        </span>
      </div>

      <div
        v-if="sidebarError"
        role="alert"
        class="sidebar-error-alert mb-2 flex items-start justify-between gap-2 rounded-lg px-2.5 py-2 text-sm"
      >
        <span class="leading-snug">{{ sidebarError }}</span>
        <button
          type="button"
          aria-label="Fechar alerta"
          class="shrink-0 opacity-80 hover:opacity-100"
          @click="sidebarError = null"
        >
          <X class="h-4 w-4" />
        </button>
      </div>

      <!-- Resultados de busca -->
      <template v-if="normalizedQuery">
        <div v-if="searchResults.length > 0" class="space-y-1">
          <div
            v-for="{ conversation, snippet } in searchResults"
            :key="conversation.id"
            :class="[
              'conv-item group relative flex cursor-pointer items-start justify-between gap-2 rounded-lg px-2.5 py-2 text-[14.5px] transition-colors',
              currentConvId === conversation.id && route.path === '/chat'
                ? 'bg-white/[0.15] text-white font-medium'
                : 'text-white/85 hover:bg-white/[0.08] hover:text-white',
            ]"
            @click="selectConversation(conversation.id)"
          >
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-1.5">
                <Pin v-if="conversation.isPinned" class="h-3.5 w-3.5 shrink-0 text-emerald-300" />
                <span class="truncate leading-snug">{{ conversation.title }}</span>
              </div>
              <p v-if="snippet" class="mt-0.5 truncate text-[13px] text-white/65">
                {{ snippet }}
              </p>
            </div>
            <span class="shrink-0 text-xs tabular-nums text-white/55">
              {{ formatConversationDate(conversation.updatedAt) }}
            </span>
          </div>
        </div>
        <p v-else class="px-2 py-6 text-center text-sm text-white/60">
          Nenhuma conversa encontrada.
        </p>
      </template>

      <!-- Lista agrupada por Fixadas e período -->
      <template v-else>
        <div v-if="groupedConversations.length > 0" class="space-y-3.5">
          <div v-for="group in groupedConversations" :key="group.key">
            <p class="px-1.5 pb-1.5 text-xs font-semibold uppercase tracking-[0.08em] text-white/55">
              {{ group.label }}
            </p>
            <div class="space-y-0.5">
              <div
                v-for="conversation in group.items"
                :key="conversation.id"
                :class="[
                  'conv-item group relative flex cursor-pointer items-center justify-between gap-2 rounded-lg px-2.5 py-2 text-[14.5px] transition-colors',
                  currentConvId === conversation.id && route.path === '/chat'
                    ? 'bg-white/[0.15] text-white font-medium'
                    : 'text-white/85 hover:bg-white/[0.08] hover:text-white',
                ]"
                @click="selectConversation(conversation.id)"
              >
                <div class="flex min-w-0 flex-1 items-center gap-2">
                  <Loader2
                    v-if="activeConversationIds.includes(conversation.id)"
                    class="h-4 w-4 shrink-0 animate-spin text-emerald-300"
                    title="Gerando resposta..."
                    aria-label="Gerando resposta"
                  />
                  <Pin
                    v-else-if="conversation.isPinned"
                    class="h-3.5 w-3.5 shrink-0 text-emerald-300"
                    aria-hidden="true"
                  />

                  <input
                    v-if="editingId === conversation.id"
                    ref="editInputRef"
                    v-model="editingTitle"
                    type="text"
                    maxlength="255"
                    aria-label="Renomear conversa"
                    class="w-full min-w-0 rounded border border-white/30 bg-black/25 px-2 py-0.5 text-[14.5px] text-white focus:border-white/60 focus:outline-none"
                    @click.stop
                    @keydown.enter.prevent="saveRename(conversation.id)"
                    @keydown.esc.prevent="cancelRename"
                    @blur="saveRename(conversation.id)"
                  />
                  <span
                    v-else
                    class="truncate leading-snug"
                    :title="conversation.title"
                    @dblclick.stop="startRename(conversation)"
                  >
                    {{ conversation.title }}
                  </span>
                </div>

                <!-- Data curta (oculta no hover/foco) -->
                <span
                  v-if="editingId !== conversation.id"
                  class="shrink-0 text-xs tabular-nums text-white/55 group-hover:hidden group-focus-within:hidden"
                >
                  {{ formatConversationDate(conversation.updatedAt) }}
                </span>

                <!-- Ações inline -->
                <div
                  v-if="editingId !== conversation.id"
                  class="hidden shrink-0 items-center gap-0.5 group-hover:flex group-focus-within:flex"
                  @click.stop
                >
                  <button
                    type="button"
                    class="rounded p-1 text-white/70 transition-colors hover:bg-white/15 hover:text-white"
                    :title="conversation.isPinned ? 'Desafixar conversa' : 'Fixar conversa'"
                    :aria-label="conversation.isPinned ? 'Desafixar conversa' : 'Fixar conversa'"
                    @click="togglePin(conversation)"
                  >
                    <PinOff v-if="conversation.isPinned" class="h-4 w-4" />
                    <Pin v-else class="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    class="rounded p-1 text-white/70 transition-colors hover:bg-white/15 hover:text-white"
                    title="Renomear conversa"
                    aria-label="Renomear conversa"
                    @click="startRename(conversation)"
                  >
                    <Pencil class="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    class="sidebar-delete-btn rounded p-1 text-white/70 transition-colors"
                    title="Excluir chat"
                    aria-label="Excluir chat"
                    @click="requestDelete(conversation)"
                  >
                    <Trash2 class="h-4 w-4" />
                  </button>
                </div>

                <!-- Botão confirmar edição -->
                <button
                  v-else
                  type="button"
                  class="shrink-0 rounded p-1 text-emerald-200 hover:bg-white/15"
                  title="Salvar título"
                  aria-label="Salvar título"
                  @mousedown.prevent="saveRename(conversation.id)"
                >
                  <Check class="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
        <p v-else class="px-2 py-6 text-center text-sm text-white/60">
          Nenhuma conversa ainda.
        </p>
      </template>
    </div>

    <div v-else class="flex-1" />

    <!-- Rodapé -->
    <div class="border-t border-white/10 px-3 pt-3 pb-3.5">
      <div class="space-y-2.5">
        <AtualizacaoDisponivel :collapsed="isEffectivelyCollapsed" />

        <button
          type="button"
          data-testid="theme-toggle-btn"
          :aria-pressed="isDark"
          :aria-label="isDark ? 'Modo Claro' : 'Modo Escuro'"
          :class="[
            'flex w-full items-center gap-3 rounded-lg border border-white/[0.14] bg-white/[0.05] text-xs font-medium uppercase tracking-[0.11em] text-white/85 transition-colors hover:bg-white/[0.11] hover:text-white',
            isEffectivelyCollapsed ? 'justify-center p-2.5' : 'px-3.5 py-2.5',
          ]"
          :title="isDark ? 'Modo Claro' : 'Modo Escuro'"
          @click="toggleTheme"
        >
          <Sun v-if="isDark" class="h-[18px] w-[18px] shrink-0 text-white/80" />
          <Moon v-else class="h-[18px] w-[18px] shrink-0 text-white/80" />
          <span v-if="!isEffectivelyCollapsed">{{ isDark ? 'Modo Claro' : 'Modo Escuro' }}</span>
        </button>
      </div>

      <template v-if="!isEffectivelyCollapsed">
        <div class="mt-3.5 mb-3 border-t border-white/10" />
        <p class="text-center text-xs leading-none text-white/55">
          Powered by <span class="font-medium text-white/85">LEDS &amp; SmartIdea</span>
        </p>
      </template>
    </div>
  </aside>
</template>

<style scoped>
.adito-sidebar {
  --sidebar-expanded-width: 360px;
}

.adito-sidebar--expanded {
  width: min(var(--sidebar-expanded-width), 85vw);
}

.icon-button--active {
  background: rgba(255, 255, 255, 0.16);
  color: #ffffff;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.22);
}

.sidebar-error-alert {
  color: #fee2e2;
  background: rgba(239, 68, 68, 0.16);
  border: 1px solid rgba(248, 113, 113, 0.35);
}

.sidebar-delete-btn:hover {
  background: rgba(239, 68, 68, 0.24);
  color: #fecaca;
}

.no-scrollbar::-webkit-scrollbar {
  display: none;
}

.no-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>
