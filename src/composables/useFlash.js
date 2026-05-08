import { onMounted, onUnmounted } from 'vue'
import { useMonitorStore } from '../stores/monitor.js'

const BLINK_MS = 500
const FLASH_MS = 150

export function useFlash() {
  const store = useMonitorStore()
  let blinkTimer = null
  let flashTimer = null

  onMounted(() => {
    blinkTimer = setInterval(() => {
      if (store.isBlinking) {
        store.toggleBlink()
      }
    }, BLINK_MS)

    flashTimer = setInterval(() => {
      if (store.isFlashing) {
        store.doFlash()
      }
    }, FLASH_MS)
  })

  onUnmounted(() => {
    if (blinkTimer) clearInterval(blinkTimer)
    if (flashTimer) clearInterval(flashTimer)
  })
}
