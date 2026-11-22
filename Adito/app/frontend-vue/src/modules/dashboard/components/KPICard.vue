<script setup lang="ts">
import type { Component } from 'vue'

interface Props {
  title: string
  value: string | number
  subtitle?: string
  icon?: Component
  trend?: {
    value: string
    positive: boolean
  }
}

defineProps<Props>()
</script>

<template>
  <div
    v-motion="{
      initial: { opacity: 0, y: 20 },
      enter: { opacity: 1, y: 0 }
    }"
    class="premium-card group relative overflow-hidden p-4 md:p-6"
  >
    <div class="relative z-10 flex items-start justify-between">
      <div class="min-w-0 flex-1 pr-2">
        <p class="eyebrow mb-1 truncate md:mb-1.5">
          {{ title }}
        </p>
        <p class="mb-1 truncate text-xl leading-tight text-primary sm:text-2xl md:mb-2 md:text-3xl">
          {{ value }}
        </p>

        <div v-if="subtitle" class="flex items-center gap-1.5">
          <p class="truncate text-[10px] font-medium text-text-secondary sm:text-xs md:text-sm">
            {{ subtitle }}
          </p>
        </div>

        <div v-if="trend" class="mt-2 flex items-center gap-1.5">
          <span :class="[
            'rounded-md px-2 py-0.5 text-[13px] font-semibold',
            trend.positive ? 'bg-green-500/10 text-green-700 dark:text-green-400' : 'bg-red-500/10 text-red-700 dark:text-red-400'
          ]">
            {{ trend.positive ? '↑' : '↓' }} {{ trend.value }}
          </span>
        </div>
      </div>

      <div v-if="icon" class="shrink-0 rounded-lg border border-border-subtle bg-surface-elevated p-2.5 sm:p-3">
        <component :is="icon" class="h-5 w-5 text-accent sm:h-6 sm:w-6" />
      </div>
    </div>
  </div>
</template>
