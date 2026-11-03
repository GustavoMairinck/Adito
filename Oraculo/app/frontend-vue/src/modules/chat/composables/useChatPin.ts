import { ref } from 'vue'
import { usePersonalDashboard } from '@/modules/dashboard/composables/usePersonalDashboard'

export function useChatPin(showToast: (msg: string, type?: string) => void) {
  const pinModalOpen = ref(false)
  const pinTitle = ref('')
  const isPinning = ref(false)
  const currentPinMessage = ref<any>(null)

  const { createWidget } = usePersonalDashboard()

  const openPinModal = (message: any, questionOriginal?: string) => {
    currentPinMessage.value = {
      ...message,
      questionOriginal: questionOriginal || message.question_temp || ''
    }
    pinTitle.value = questionOriginal
      ? questionOriginal.substring(0, 50)
      : message.text
        ? message.text.substring(0, 50)
        : 'Análise'
    pinModalOpen.value = true
  }

  const closePin = () => {
    pinModalOpen.value = false
    currentPinMessage.value = null
    pinTitle.value = ''
  }

  const savePin = async () => {
    isPinning.value = true
    try {
      const chartType = currentPinMessage.value?.isScalarResult
        ? 'metric_card'
        : currentPinMessage.value?.chart
          ? 'bar'
          : 'table'

      const grid_w = chartType === 'metric_card' ? 4 : 6
      const grid_h = chartType === 'metric_card' ? 6 : (chartType === 'table' ? 8 : 12)

      const payload = {
        title: pinTitle.value,
        question_original: currentPinMessage.value?.questionOriginal || 'Análise Pin',
        sql_validated: currentPinMessage.value?.sql || '',
        chart_type: chartType as any,
        grid_w,
        grid_h,
        grid_x: 0,
        grid_y: 0,
        size: 'medium'
      }

      await createWidget(payload)

      showToast('Fixado com sucesso', 'success')
      closePin()
    } catch (e: any) {
      console.error('Erro ao fixar no dashboard:', e)
      showToast('Erro ao fixar', 'error')
    } finally {
      isPinning.value = false
    }
  }

  return {
    pinModalOpen,
    pinTitle,
    isPinning,
    openPinModal,
    savePin,
    closePin
  }
}

