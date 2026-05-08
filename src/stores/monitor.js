import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '../api.js'

function sessionSig(sessions) {
  const parts = sessions.map(s => {
    const tasks = s.tasks.map(t => `${t.id}:${t.status}:${t.subject}`).join('|')
    return `${s.session_id}:${s.status}:${s.is_alive}:${tasks}`
  })
  return parts.join('||')
}

export const useMonitorStore = defineStore('monitor', () => {
  const sessions = ref([])
  const lastSig = ref('')
  const lastSessions = ref([])
  const changedSessions = ref(new Set())
  const newSessions = ref(new Set())
  const blinkPhase = ref(false)
  const flashCount = ref(0)
  const isFlashing = ref(false)
  const isBlinking = ref(false)
  const hideDead = ref(false)

  const filteredSessions = computed(() => {
    if (hideDead.value) {
      return sessions.value.filter(s => s.is_alive)
    }
    return sessions.value
  })

  const totalTasks = computed(() => {
    return sessions.value.reduce((sum, s) => sum + (s.tasks?.length || 0), 0)
  })

  const hasChanges = computed(() => {
    return changedSessions.value.size > 0 || newSessions.value.size > 0
  })

  async function refresh() {
    const data = await api.loadSessions()
    sessions.value = data
    const sig = sessionSig(data)

    if (lastSig.value && lastSig.value !== sig) {
      const oldMap = new Map(lastSessions.value.map(s => [s.session_id, s]))
      for (const s of data) {
        const old = oldMap.get(s.session_id)
        if (!old) {
          newSessions.value.add(s.session_id)
        } else if (s.status !== old.status || s.is_alive !== old.is_alive || s.tasks.length !== old.tasks.length) {
          changedSessions.value.add(s.session_id)
        }
      }
    }

    lastSessions.value = JSON.parse(JSON.stringify(data))
    lastSig.value = sig

    if (hasChanges.value && !isBlinking.value) {
      isBlinking.value = true
    }
  }

  function acknowledgeChange(sessionId) {
    changedSessions.value.delete(sessionId)
    newSessions.value.delete(sessionId)
    if (!hasChanges.value) {
      isBlinking.value = false
    }
  }

  function toggleBlink() {
    blinkPhase.value = !blinkPhase.value
  }

  function startFlash() {
    isFlashing.value = true
    flashCount.value = 0
  }

  function stopFlash() {
    isFlashing.value = false
  }

  function doFlash() {
    flashCount.value++
  }

  function hideDeadSessions() {
    hideDead.value = true
  }

  function showDeadSessions() {
    hideDead.value = false
  }

  return {
    sessions,
    filteredSessions,
    lastSig,
    lastSessions,
    changedSessions,
    newSessions,
    blinkPhase,
    flashCount,
    isFlashing,
    isBlinking,
    hideDead,
    totalTasks,
    hasChanges,
    refresh,
    acknowledgeChange,
    toggleBlink,
    startFlash,
    stopFlash,
    doFlash,
    hideDeadSessions,
    showDeadSessions,
  }
})
