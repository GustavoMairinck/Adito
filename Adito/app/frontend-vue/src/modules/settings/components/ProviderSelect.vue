<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Check, ChevronDown, Cpu, Globe, HardDrive, KeyRound, Sparkles } from 'lucide-vue-next'
import type { LlmProviderSpec } from '@/common/api/llmKey'

const props = defineProps<{
  id?: string
  labelledBy?: string
  modelValue: string
  providers: LlmProviderSpec[]
  activeProviderId?: string
  hasKeyByProvider?: Record<string, boolean>
  disabled?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  change: [value: string]
}>()

const rootRef = ref<HTMLElement | null>(null)
const triggerRef = ref<HTMLButtonElement | null>(null)
const listRef = ref<HTMLUListElement | null>(null)
const open = ref(false)
const highlightedIndex = ref(0)

const selectedProvider = computed<LlmProviderSpec>(
  () => props.providers.find((p) => p.id === props.modelValue) ?? props.providers[0]
)

const selectedIndex = computed(() =>
  Math.max(0, props.providers.findIndex((p) => p.id === props.modelValue))
)

function hasSavedKey(id: string): boolean {
  return Boolean(props.hasKeyByProvider?.[id])
}

function isInUse(id: string): boolean {
  return Boolean(props.activeProviderId && props.activeProviderId === id)
}

function providerIcon(spec: LlmProviderSpec) {
  if (spec.id === 'gemini') return Sparkles
  if (spec.id === 'ollama') return HardDrive
  if (spec.id === 'openrouter') return Globe
  return Cpu
}

function subtitleFor(spec: LlmProviderSpec): string {
  return spec.default_model || spec.base_url
}

function openMenu() {
  if (props.disabled) return
  open.value = true
  highlightedIndex.value = selectedIndex.value
  nextTick(() => {
    const activeEl = listRef.value?.querySelector<HTMLElement>('[data-highlighted="true"]')
    activeEl?.scrollIntoView({ block: 'nearest' })
  })
}

function closeMenu(restoreFocus = false) {
  open.value = false
  if (restoreFocus) {
    nextTick(() => triggerRef.value?.focus())
  }
}

function toggleMenu() {
  if (open.value) closeMenu()
  else openMenu()
}

function selectProvider(id: string) {
  const changed = id !== props.modelValue
  emit('update:modelValue', id)
  if (changed) emit('change', id)
  closeMenu(true)
}

function onKeydown(event: KeyboardEvent) {
  if (props.disabled) return
  const total = props.providers.length
  if (!total) return

  if (!open.value) {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp' || event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      openMenu()
    }
    return
  }

  if (event.key === 'Escape') {
    event.preventDefault()
    closeMenu(true)
    return
  }
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    highlightedIndex.value = (highlightedIndex.value + 1) % total
    return
  }
  if (event.key === 'ArrowUp') {
    event.preventDefault()
    highlightedIndex.value = (highlightedIndex.value - 1 + total) % total
    return
  }
  if (event.key === 'Home') {
    event.preventDefault()
    highlightedIndex.value = 0
    return
  }
  if (event.key === 'End') {
    event.preventDefault()
    highlightedIndex.value = total - 1
    return
  }
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    const target = props.providers[highlightedIndex.value]
    if (target) selectProvider(target.id)
  }
}

function onClickOutside(event: MouseEvent) {
  if (!open.value) return
  if (rootRef.value && !rootRef.value.contains(event.target as Node)) {
    closeMenu()
  }
}

watch(() => props.disabled, (isDisabled) => {
  if (isDisabled) open.value = false
})

onMounted(() => {
  document.addEventListener('mousedown', onClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('mousedown', onClickOutside)
})

const listboxId = computed(() => `${props.id || 'llm-provider'}-listbox`)
</script>

<template>
  <div ref="rootRef" class="relative w-full" @keydown="onKeydown">
    <button
      :id="id"
      ref="triggerRef"
      type="button"
      role="combobox"
      :aria-labelledby="labelledBy"
      :aria-expanded="open"
      aria-haspopup="listbox"
      :aria-controls="listboxId"
      :disabled="disabled"
      :class="[
        'flex w-full min-h-[42px] items-center justify-between gap-2.5 rounded-lg border px-3 py-2 text-left text-sm transition-all duration-150',
        'bg-surface text-text-primary shadow-card',
        open
          ? 'border-[var(--brand-primary)] ring-2 ring-[var(--brand-primary)]/20 dark:border-[#68d388] dark:ring-[#68d388]/20'
          : 'border-border-subtle hover:border-[var(--brand-primary)]/50 dark:hover:border-[#68d388]/50',
        disabled ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer',
      ]"
      @click="toggleMenu"
    >
      <span class="flex min-w-0 items-center gap-2.5">
        <span
          class="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-[var(--brand-primary)]/20 bg-[var(--accent-light)] text-[var(--brand-primary)] dark:border-[#68d388]/25 dark:text-[#68d388]"
        >
          <component :is="providerIcon(selectedProvider)" class="h-3.5 w-3.5" stroke-width="2" />
        </span>
        <span class="flex min-w-0 flex-col">
          <span class="truncate font-medium leading-tight text-text-primary">
            {{ selectedProvider.label }}
          </span>
          <span class="truncate font-mono text-[11px] leading-tight text-text-muted">
            {{ subtitleFor(selectedProvider) }}
          </span>
        </span>
      </span>

      <span class="flex shrink-0 items-center gap-1.5">
        <span
          v-if="isInUse(selectedProvider.id)"
          class="inline-flex items-center gap-1.5 rounded-full bg-[var(--brand-primary)] px-2.5 py-0.5 text-[10px] font-semibold tracking-tight text-white shadow-xs"
        >
          <span class="h-1.5 w-1.5 rounded-full bg-[#8ef0aa]" aria-hidden="true" />
          Em uso
        </span>
        <span
          v-else-if="hasSavedKey(selectedProvider.id)"
          class="inline-flex items-center gap-1 rounded-full border border-[var(--brand-primary)]/25 bg-[var(--accent-light)] px-2 py-0.5 text-[10px] font-semibold tracking-tight text-[var(--brand-primary)] dark:border-[#68d388]/30 dark:text-[#68d388]"
        >
          <KeyRound class="h-2.5 w-2.5" />
          Salva
        </span>
        <span
          v-else-if="selectedProvider.id === 'ollama'"
          class="rounded-full border border-[var(--brand-primary)]/25 bg-[var(--accent-light)] px-2 py-0.5 text-[10px] font-semibold tracking-tight text-[var(--brand-primary)] dark:border-[#68d388]/30 dark:text-[#68d388]"
        >
          Local
        </span>
        <ChevronDown
          :class="[
            'h-4 w-4 text-text-muted transition-transform duration-150',
            open ? 'rotate-180 text-[var(--brand-primary)] dark:text-[#68d388]' : '',
          ]"
        />
      </span>
    </button>

    <Transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="opacity-0 -translate-y-1 scale-[0.99]"
      enter-to-class="opacity-100 translate-y-0 scale-100"
      leave-active-class="transition duration-100 ease-in"
      leave-from-class="opacity-100 translate-y-0 scale-100"
      leave-to-class="opacity-0 -translate-y-1 scale-[0.99]"
    >
      <ul
        v-if="open"
        :id="listboxId"
        ref="listRef"
        role="listbox"
        :aria-labelledby="labelledBy"
        class="absolute left-0 right-0 z-50 mt-1.5 max-h-72 overflow-y-auto rounded-xl border border-border-standard/80 bg-surface p-1.5 shadow-elevated focus:outline-none"
      >
        <li
          v-for="(spec, idx) in providers"
          :key="spec.id"
          role="option"
          :aria-selected="spec.id === modelValue"
          :data-highlighted="idx === highlightedIndex"
          :class="[
            'group flex cursor-pointer items-center justify-between gap-2 rounded-lg px-2.5 py-2 text-sm transition-colors duration-100',
            spec.id === modelValue
              ? 'bg-[var(--conv-selected)] text-text-primary'
              : idx === highlightedIndex
                ? 'bg-[var(--conv-hover)] text-text-primary'
                : 'text-text-primary hover:bg-[var(--conv-hover)]',
          ]"
          @mouseenter="highlightedIndex = idx"
          @mousedown.prevent="selectProvider(spec.id)"
        >
          <span class="flex min-w-0 items-center gap-2.5">
            <span
              :class="[
                'flex h-7 w-7 shrink-0 items-center justify-center rounded-md border transition-colors',
                spec.id === modelValue
                  ? 'border-[var(--brand-primary)]/30 bg-[var(--accent-light)] text-[var(--brand-primary)] dark:border-[#68d388]/35 dark:text-[#68d388]'
                  : 'border-border-subtle bg-surface-elevated text-text-secondary group-hover:border-[var(--brand-primary)]/25 group-hover:text-[var(--brand-primary)] dark:group-hover:text-[#68d388]',
              ]"
            >
              <component :is="providerIcon(spec)" class="h-3.5 w-3.5" stroke-width="2" />
            </span>

            <span class="flex min-w-0 flex-col">
              <span
                :class="[
                  'truncate leading-tight',
                  spec.id === modelValue ? 'font-semibold text-[var(--brand-dark)] dark:text-[#F0F4F1]' : 'font-medium text-text-primary',
                ]"
              >
                {{ spec.label }}
              </span>
              <span class="truncate font-mono text-[11px] leading-tight text-text-muted">
                {{ subtitleFor(spec) }}
              </span>
            </span>
          </span>

          <span class="flex shrink-0 items-center gap-1.5">
            <span
              v-if="isInUse(spec.id)"
              class="inline-flex items-center gap-1.5 rounded-full bg-[var(--brand-primary)] px-2.5 py-0.5 text-[10px] font-semibold text-white shadow-xs"
            >
              <span class="h-1.5 w-1.5 rounded-full bg-[#8ef0aa]" aria-hidden="true" />
              Em uso
            </span>
            <span
              v-else-if="hasSavedKey(spec.id)"
              class="inline-flex items-center gap-1 rounded-full border border-[var(--brand-primary)]/25 bg-[var(--accent-light)] px-2 py-0.5 text-[10px] font-semibold text-[var(--brand-primary)] dark:border-[#68d388]/30 dark:text-[#68d388]"
            >
              <KeyRound class="h-2.5 w-2.5" />
              Chave salva
            </span>
            <span
              v-else-if="spec.id === 'ollama'"
              class="rounded-full border border-[var(--brand-primary)]/25 bg-[var(--accent-light)] px-2 py-0.5 text-[10px] font-semibold text-[var(--brand-primary)] dark:border-[#68d388]/30 dark:text-[#68d388]"
            >
              Local
            </span>
            <Check
              v-if="spec.id === modelValue"
              class="h-4 w-4 text-[var(--brand-primary)] dark:text-[#68d388]"
              stroke-width="2.5"
            />
          </span>
        </li>
      </ul>
    </Transition>
  </div>
</template>
