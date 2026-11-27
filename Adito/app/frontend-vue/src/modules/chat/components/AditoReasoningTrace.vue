<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { AlertTriangle, Check, ChevronDown, Copy, Loader2 } from 'lucide-vue-next'
import BrandIcon from '@/common/components/BrandIcon.vue'
import type { ReasoningTrace } from '@/modules/chat/types'
import { formatTraceDuration, formatTraceTime } from '@/modules/chat/utils/trace'

const props = defineProps<{
  trace: ReasoningTrace
  isLoading?: boolean
  hasFinalContent?: boolean
  timestamp?: string
}>()

const hasError = computed(() => props.trace.steps.some((step) => step.status === 'error'))
const activeStep = computed(
  () =>
    props.trace.steps.find((step) => step.status === 'running') ??
    props.trace.steps[props.trace.steps.length - 1],
)

const isOpen = ref(Boolean(props.isLoading || (hasError.value && !props.hasFinalContent)))
const userToggled = ref(false)
const copiedStepId = ref<string | null>(null)

watch(
  () => [props.isLoading, props.hasFinalContent, hasError.value] as const,
  ([loading, hasContent, errored], prev) => {
    if (userToggled.value) return
    if (loading && !hasContent) {
      isOpen.value = true
      return
    }
    if (hasContent && !prev?.[1]) {
      isOpen.value = false
      return
    }
    if (!loading) {
      isOpen.value = errored && !hasContent
    }
  },
)

function toggleOpen() {
  userToggled.value = true
  isOpen.value = !isOpen.value
}

const headerLabel = computed(() => {
  if (props.isLoading) {
    return activeStep.value?.headerStatus || 'Analisando contexto...'
  }
  if (hasError.value) {
    return 'Etapas com alerta'
  }
  if (props.trace.compact) {
    return 'Processo de análise'
  }
  return 'Etapas da consulta'
})

const durationText = computed(() => formatTraceDuration(props.trace.durationMs))
const timeText = computed(() => formatTraceTime(props.timestamp || props.trace.finishedAt))

async function copyCode(stepId: string, code: string) {
  if (!code) return
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(code)
    } else {
      const textarea = document.createElement('textarea')
      textarea.value = code
      textarea.style.position = 'absolute'
      textarea.style.left = '-999999px'
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      textarea.remove()
    }
    copiedStepId.value = stepId
    setTimeout(() => {
      if (copiedStepId.value === stepId) copiedStepId.value = null
    }, 2000)
  } catch (err) {
    console.error('Erro ao copiar código SQL:', err)
  }
}
</script>

<template>
  <div class="reasoning-trace mb-3" data-testid="adito-reasoning-trace">
    <div class="flex items-center justify-between gap-2 pr-1">
      <button
        type="button"
        class="group flex min-w-0 items-center gap-2.5 rounded-xl px-1.5 py-1 text-left transition-colors hover:bg-surface-elevated/70"
        :aria-expanded="isOpen"
        @click="toggleOpen"
      >
        <div class="relative flex h-9 w-9 shrink-0 items-center justify-center">
          <div v-if="isLoading" class="trace-brand-wrapper">
            <BrandIcon alt="" class="relative z-10 h-7 w-7" />
            <div class="trace-brand-ring" />
            <span class="trace-brand-pulse" aria-hidden="true" />
          </div>
          <BrandIcon v-else alt="" class="h-8 w-8" />
        </div>

        <div class="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-0.5">
          <span class="font-semibold tracking-[-0.03em] text-text-primary">Adito</span>
          <span class="text-text-muted" aria-hidden="true">•</span>
          <span
            :class="[
              'text-xs font-medium',
              hasError && !isLoading
                ? 'text-amber-700 dark:text-amber-300'
                : 'text-text-secondary',
            ]"
          >
            {{ headerLabel }}
          </span>
          <span
            v-if="!isLoading && (durationText || timeText)"
            class="text-[11px] text-text-muted tabular-nums"
          >
            <template v-if="durationText">{{ durationText }}</template>
            <template v-if="durationText && timeText"> · </template>
            <template v-if="timeText">{{ timeText }}</template>
          </span>
          <ChevronDown
            :class="[
              'h-3.5 w-3.5 shrink-0 text-text-muted transition-transform duration-200',
              isOpen ? 'rotate-180' : '',
            ]"
          />
        </div>
      </button>

      <div class="flex shrink-0 items-center gap-1.5">
        <slot name="actions" />
      </div>
    </div>

    <div
      class="trace-accordion"
      :class="{ 'trace-accordion--open': isOpen }"
      :aria-hidden="!isOpen"
    >
      <div class="trace-accordion-inner">
        <div class="mt-2 rounded-xl border border-border-subtle bg-surface/80 px-4 py-3 shadow-xs">
          <ol class="relative space-y-3">
            <li
              v-for="(step, idx) in trace.steps"
              :key="step.id"
              class="relative pl-6"
              :data-step-id="step.id"
              :data-step-status="step.status"
            >
              <span
                v-if="idx < trace.steps.length - 1"
                class="trace-guide-line"
                aria-hidden="true"
              />

              <span
                :class="[
                  'absolute left-0 top-0.5 flex h-4 w-4 items-center justify-center rounded-full border',
                  step.status === 'done'
                    ? 'border-[var(--accent)]/40 bg-[var(--accent-light)] text-[var(--accent)]'
                    : step.status === 'error'
                      ? 'border-amber-400/50 bg-amber-100/70 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300'
                      : 'border-[var(--accent)]/50 bg-surface text-[var(--accent)]',
                ]"
                aria-hidden="true"
              >
                <Check v-if="step.status === 'done'" class="h-2.5 w-2.5" stroke-width="2.5" />
                <AlertTriangle v-else-if="step.status === 'error'" class="h-2.5 w-2.5" />
                <Loader2 v-else class="h-2.5 w-2.5 animate-spin" />
              </span>

              <div class="min-w-0">
                <div class="flex items-center gap-2">
                  <span class="text-xs font-semibold text-text-primary">{{ step.title }}</span>
                  <span
                    v-if="step.status === 'running'"
                    class="h-1.5 w-1.5 rounded-full bg-[var(--accent)] trace-dot-pulse"
                    aria-hidden="true"
                  />
                </div>
                <p v-if="step.subtitle" class="mt-0.5 text-xs text-text-secondary">
                  {{ step.subtitle }}
                </p>

                <ul v-if="step.details.length" class="mt-1.5 space-y-1">
                  <li
                    v-for="(detail, detailIdx) in step.details"
                    :key="`${step.id}-detail-${detailIdx}`"
                    class="text-[11px] leading-relaxed text-text-muted"
                  >
                    {{ detail }}
                  </li>
                </ul>

                <div
                  v-if="step.code"
                  class="mt-2 overflow-hidden rounded-lg border border-border-subtle bg-surface-elevated/70"
                >
                  <div class="flex items-center justify-between border-b border-border-subtle/70 px-2.5 py-1">
                    <span class="font-mono text-[10px] font-semibold uppercase tracking-wider text-text-muted">
                      {{ step.language || 'sql' }}
                    </span>
                    <button
                      type="button"
                      class="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-semibold text-text-secondary transition-colors hover:bg-surface hover:text-text-primary"
                      :title="copiedStepId === step.id ? 'SQL copiado' : 'Copiar SQL'"
                      @click.stop="copyCode(step.id, step.code)"
                    >
                      <Check v-if="copiedStepId === step.id" class="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
                      <Copy v-else class="h-3 w-3" />
                      <span>{{ copiedStepId === step.id ? 'Copiado' : 'Copiar' }}</span>
                    </button>
                  </div>
                  <pre class="overflow-x-auto p-2.5 font-mono text-[11px] leading-relaxed text-text-primary whitespace-pre-wrap">{{ step.code }}</pre>
                </div>
              </div>
            </li>
          </ol>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.trace-brand-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.trace-brand-ring {
  position: absolute;
  inset: -4px;
  border-radius: 9999px;
  border: 2px solid var(--accent);
  border-top-color: transparent;
  border-right-color: transparent;
  animation: trace-spin 0.85s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}

.trace-brand-pulse {
  position: absolute;
  inset: -2px;
  border-radius: 9999px;
  background: color-mix(in srgb, var(--accent) 20%, transparent);
  animation: trace-pulse 1.6s ease-in-out infinite;
}

.trace-dot-pulse {
  animation: trace-pulse 1.2s ease-in-out infinite;
}

.trace-guide-line {
  position: absolute;
  left: 7px;
  top: 18px;
  bottom: -14px;
  width: 1px;
  background: var(--border-subtle);
}

.trace-accordion {
  display: grid;
  grid-template-rows: 0fr;
  opacity: 0;
  transition: grid-template-rows 200ms ease, opacity 180ms ease;
}

.trace-accordion--open {
  grid-template-rows: 1fr;
  opacity: 1;
}

.trace-accordion-inner {
  overflow: hidden;
}

@keyframes trace-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes trace-pulse {
  0%, 100% { opacity: 0.35; transform: scale(0.95); }
  50% { opacity: 0.9; transform: scale(1.08); }
}

@media (prefers-reduced-motion: reduce) {
  .trace-brand-ring,
  .trace-brand-pulse,
  .trace-dot-pulse {
    animation: none;
  }
  .trace-accordion {
    transition: none;
  }
}
</style>
