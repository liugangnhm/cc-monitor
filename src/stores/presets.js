import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api.js'

export const usePresetsStore = defineStore('presets', () => {
  const presets = ref([])
  const loading = ref(false)

  async function load() {
    loading.value = true
    try {
      presets.value = await api.loadPresets()
    } finally {
      loading.value = false
    }
  }

  return {
    presets,
    loading,
    load,
  }
})
