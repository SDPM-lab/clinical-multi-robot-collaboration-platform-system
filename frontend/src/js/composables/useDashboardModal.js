import { computed, ref, watch } from 'vue'

export function useDashboardModal() {
  const activeModal = ref('')
  const resultTitle = ref('')
  const confirmMessage = ref('')

  const isModalOpen = computed({
    get: () => activeModal.value !== '',
    set: (value) => { if (!value) activeModal.value = '' },
  })

  const modalTitle = computed(() => {
    if (activeModal.value === 'add') return '新增任務'
    if (activeModal.value === 'cancel') return '取消任務確認'
    if (activeModal.value === 'result') return resultTitle.value || '完成'
    if (activeModal.value === 'emergencyStop') return '緊急停止確認'
    if (activeModal.value === 'emergencyStopReconfirm') return '再次確認緊急停止'
    if (activeModal.value === 'alertDetail') return '通知詳細資訊'
    if (activeModal.value === 'newRobot') return '發現新機器人'
    if (activeModal.value === 'connectionFailed') return '連線失敗'
    return ''
  })

  watch(isModalOpen, (open) => {
    if (typeof document !== 'undefined') {
      document.body.style.overflow = open ? 'hidden' : ''
    }
  })

  const openModal = (name) => { activeModal.value = name }
  const closeModal = () => { activeModal.value = '' }

  return {
    activeModal,
    isModalOpen,
    modalTitle,
    resultTitle,
    confirmMessage,
    openModal,
    closeModal,
  }
}
