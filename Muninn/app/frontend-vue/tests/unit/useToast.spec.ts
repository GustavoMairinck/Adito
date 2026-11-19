import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useToast } from '@/common/composables/useToast'

describe('common/composables/useToast', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('exibe toast com tipo padrão info e limpa automaticamente após 3 segundos', () => {
    const { toast, showToast } = useToast()
    expect(toast.value).toBeNull()

    showToast('Chave salva com sucesso', 'success')
    expect(toast.value).toEqual({ message: 'Chave salva com sucesso', type: 'success' })

    vi.advanceTimersByTime(3000)
    expect(toast.value).toBeNull()
  })
})
