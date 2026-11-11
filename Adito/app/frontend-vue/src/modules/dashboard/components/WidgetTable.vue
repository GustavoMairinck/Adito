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
        <tr class="border-b border-gray-100 dark:border-gray-800 bg-slate-50/50 dark:bg-white/2">
          <th v-for="key in keys" :key="key" class="text-left py-3 px-4 text-primary dark:text-gray-300 font-bold uppercase tracking-[1px] text-[10px]">
            {{ key }}
          </th>
        </tr>
      <tbody>
        <tr v-for="(row, i) in data.slice(0, 10)" :key="i" class="border-b border-gray-100 dark:border-gray-800 transition-colors hover:bg-slate-50 dark:hover:bg-white/5">
          <td v-for="key in keys" :key="key" class="py-2 px-3 text-gray-700 dark:text-gray-300 font-medium">
            {{ row[key] }}
          </td>
        </tr>
      </tbody>
    </table>
    <p v-if="data.length > 10" class="text-[9px] text-center text-muted-foreground mt-2 uppercase tracking-tighter opacity-50">
      Exibindo as primeiras 10 linhas
    </p>
  </div>
</template>
