<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { SlidersHorizontal, Search, X } from 'lucide-vue-next'
import type { Filters } from '../composables/useDashboardData'

interface Props {
  filtros: Filters
  anosDisponiveis: string[]
  areasDisponiveis: string[]
  modalidadesDisponiveis: string[]
  statusDisponiveis: string[]
}

const props = defineProps<Props>()
const emit = defineEmits(['update:filtros', 'clear'])

const projetoInput = ref(props.filtros.projeto || '')

watch(() => props.filtros.projeto, (newVal) => {
  projetoInput.value = newVal || ''
})

const temFiltroAtivo = computed(() => Object.values(props.filtros).some(v => v !== ''))

function handleSelect(key: keyof Filters, event: Event) {
  const value = (event.target as HTMLSelectElement).value
  emit('update:filtros', { ...props.filtros, [key]: value })
}

function aplicarProjeto() {
  if (projetoInput.value !== props.filtros.projeto) {
    emit('update:filtros', { ...props.filtros, projeto: projetoInput.value })
  }
}

function limpar() {
  projetoInput.value = ''
  emit('clear')
}

const selectCls = `w-full min-h-[44px] rounded-lg border border-border-subtle bg-surface
  px-3 text-sm text-primary outline-none transition-colors focus:border-accent
  dark:[&>option]:bg-slate-900 dark:[&>option]:text-gray-100`
</script>

<template>
  <div
    v-motion="{
      initial: { opacity: 0, y: -8 },
      enter: { opacity: 1, y: 0 }
    }"
    class="mb-8 grid grid-cols-1 items-end gap-3 rounded-2xl border border-border-subtle bg-surface px-4 py-4 shadow-premium sm:grid-cols-2 md:grid-cols-3 md:gap-5 md:px-6 xl:flex xl:flex-wrap"
  >
    <div class="flex items-center gap-2 self-end pb-2.5 text-accent sm:col-span-2 md:col-span-1 xl:col-span-1">
      <SlidersHorizontal class="h-4 w-4" />
      <span class="eyebrow text-primary">Filtros</span>
    </div>

    <div class="flex min-w-[120px] flex-1 flex-col gap-1.5 focus-within:text-accent transition-colors">
      <label class="eyebrow px-1">Ano</label>
      <select :value="filtros.ano" :class="selectCls" @change="handleSelect('ano', $event)">
        <option value="">Todos</option>
        <option v-for="a in anosDisponiveis" :key="a" :value="a">{{ a }}</option>
      </select>
    </div>

    <div class="flex min-w-[140px] flex-1 flex-col gap-1.5 focus-within:text-accent transition-colors">
      <label class="eyebrow px-1">Porte</label>
      <select :value="filtros.status" :class="selectCls" @change="handleSelect('status', $event)">
        <option value="">Todos</option>
        <option v-for="s in statusDisponiveis" :key="s" :value="s">{{ s }}</option>
      </select>
    </div>

    <div class="flex min-w-[160px] flex-1 flex-col gap-1.5 focus-within:text-accent transition-colors">
      <label class="eyebrow px-1">Categoria</label>
      <select :value="filtros.area" :class="selectCls" @change="handleSelect('area', $event)">
        <option value="">Todas</option>
        <option v-for="a in areasDisponiveis" :key="a" :value="a">{{ a }}</option>
      </select>
    </div>

    <div class="flex min-w-[200px] flex-1 flex-col gap-1.5 focus-within:text-accent transition-colors sm:col-span-2 md:col-span-1">
      <label class="eyebrow px-1">Busca direta</label>
      <div class="relative">
        <input
          v-model="projetoInput"
          :class="[selectCls, 'pr-10']"
          placeholder="Produto ou cliente..."
          type="text"
          @blur="aplicarProjeto"
          @keydown.enter="aplicarProjeto"
        />
        <Search class="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted opacity-60" />
      </div>
    </div>

    <div class="flex items-center gap-3 self-end pb-2.5 sm:col-span-2 md:col-span-1 md:ml-auto xl:col-span-1">
      <transition
        enter-active-class="transition duration-200 ease-out"
        enter-from-class="opacity-0 -translate-x-2"
        enter-to-class="opacity-100 translate-x-0"
        leave-active-class="transition duration-150 ease-in"
        leave-from-class="opacity-100 translate-x-0"
        leave-to-class="opacity-0 -translate-x-2"
      >
        <button
          v-if="temFiltroAtivo"
          class="flex items-center gap-1.5 px-2 text-xs font-semibold uppercase tracking-[0.14em] text-text-muted transition-all active:scale-95 hover:text-red-500"
          @click="limpar"
        >
          <X class="h-3.5 w-3.5" />
          Limpar
        </button>
      </transition>

      <transition
        enter-active-class="transition duration-200 ease-out"
        enter-from-class="opacity-0 scale-90"
        enter-to-class="opacity-100 scale-100"
        leave-active-class="transition duration-150 ease-in"
        leave-from-class="opacity-100 scale-100"
        leave-to-class="opacity-0 scale-90"
      >
        <span
          v-if="temFiltroAtivo"
          class="whitespace-nowrap rounded-md border border-accent/20 bg-accent/8 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-accent"
        >
          {{ Object.values(filtros).filter(v => v).length }} ativo(s)
        </span>
      </transition>
    </div>
  </div>
</template>

<style scoped>
select {
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%238a867f'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'%3E%3C/path%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 0.75rem center;
  background-size: 1rem;
}
</style>
