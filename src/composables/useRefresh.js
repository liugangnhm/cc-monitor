import { onMounted, onUnmounted } from 'vue'
import { useMonitorStore } from '../stores/monitor.js'

const REFRESH_MS = 2000

export function useRefresh() {
  const store = useMonitorStore()
  let timer = null

  async function tick() {
    await store.refresh()
  }

  onMounted(() => {
    tick()
    timer = setInterval(tick, REFRESH_MS)
  })

  onUnmounted(() => {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  })
}
