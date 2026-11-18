<script setup lang="ts">
// No imports needed

interface Props {
  data: any[]
}

const props = defineProps<Props>()
const keys = props.data && props.data.length > 0 ? Object.keys(props.data[0]) : []
</script>

<template>
  <div v-if="!data || data.length === 0" class="flex flex-col items-center justify-center h-full py-8 text-gray-400">
    <p class="text-sm italic">Sem dados disponíveis</p>
  </div>

  <div v-else class="overflow-x-auto p-4 max-h-[400px]">
    <table class="w-full text-sm">
      <thead>
        <tr class="border-b border-border-subtle bg-surface-elevated/60">
          <th v-for="key in keys" :key="key" class="text-left py-3 px-4 text-text-primary font-bold uppercase tracking-[1px] text-[10px]">
            {{ key }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, i) in data.slice(0, 10)" :key="i" class="border-b border-border-subtle/60 transition-colors hover:bg-surface-elevated/40">
          <td v-for="key in keys" :key="key" class="py-2 px-3 text-text-secondary font-medium">
            {{ row[key] }}
          </td>
        </tr>
      </tbody>
    </table>
    <p v-if="data.length > 10" class="text-[9px] text-center text-text-muted mt-2 uppercase tracking-tighter">
      Exibindo as primeiras 10 linhas
    </p>
  </div>
</template>
