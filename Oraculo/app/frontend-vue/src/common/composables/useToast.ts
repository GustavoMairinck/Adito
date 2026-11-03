import { ref } from 'vue'

export function useToast() {
  const toast = ref<{ message: string, type: string } | null>(null)
  
  const showToast = (message: string, type: string = 'info') => {
    toast.value = { message, type }
    setTimeout(() => {
      toast.value = null
    }, 3000)
  }
  
  return { toast, showToast }
}
