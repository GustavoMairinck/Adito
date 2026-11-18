<script setup lang="ts">
withDefaults(defineProps<{ alt?: string }>(), {
  alt: 'Muninn'
})
</script>

<template>
  <span class="inline-flex shrink-0">
    <img
      src="/brand/muninn-light.png"
      :alt="alt"
      class="h-full w-full object-contain dark:hidden"
      draggable="false"
    />
    <img
      src="/brand/muninn-dark.png"
      :alt="alt"
      class="hidden h-full w-full object-contain dark:block"
      draggable="false"
    />
  </span>
</template>
