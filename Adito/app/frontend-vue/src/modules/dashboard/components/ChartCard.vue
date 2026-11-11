<script setup lang="ts">
interface Props {
  title: string
  loading?: boolean
}

defineProps<Props>()
</script>

<template>
  <div class="premium-card flex h-full flex-col">
    <div class="flex items-center justify-between px-6 pb-0 pt-5">
      <h3 class="text-base font-semibold text-primary md:text-lg">
        {{ title }}
      </h3>

      <div class="flex items-center gap-2">
        <slot name="actions" />
      </div>
    </div>

    <div class="relative min-h-[300px] flex-1 px-6 pb-6 pt-2">
      <div v-if="loading" class="absolute inset-0 z-10 flex items-center justify-center bg-surface/80 backdrop-blur-sm transition-opacity">
        <div class="flex h-[200px] w-full animate-pulse items-end gap-1.5 px-4 pb-2">
          <div
            v-for="h in [40, 70, 55, 85, 100, 60, 75, 45, 90, 65]"
            :key="h"
            class="flex-1 rounded-t-sm bg-surface-elevated"
            :style="{ height: `${h}%` }"
          />
        </div>
      </div>

      <slot />
    </div>
  </div>
</template>
