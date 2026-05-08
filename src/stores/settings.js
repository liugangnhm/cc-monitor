import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useSettingsStore = defineStore('settings', () => {
  const viewMode = ref('compact')
  const history = ref([])

  function setViewMode(mode) {
    viewMode.value = mode
  }

  function toggleViewMode() {
    viewMode.value = viewMode.value === 'compact' ? 'detail' : 'compact'
  }

  return {
    viewMode,
    history,
    setViewMode,
    toggleViewMode,
  }
})
