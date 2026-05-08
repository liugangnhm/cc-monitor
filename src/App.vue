<template>
  <div class="ccm-app" :style="{ opacity: appOpacity }" @mouseenter="onMouseEnter" @mouseleave="onMouseLeave" @click="onAppClick">
    <div class="accent-line"></div>
    <TitleBar
      :total-tasks="monitor.totalTasks"
      :view-mode="settings.viewMode"
      @settings="showPresetManager = true"
      @add="showAddWorkspace = true"
      @toggleView="onToggleView"
      @close="closeWindow"
    />
    <div class="content" :class="settings.viewMode">
      <div v-if="monitor.filteredSessions.length === 0" class="empty">
        未检测到活跃 Session
      </div>
      <template v-else-if="settings.viewMode === 'compact'">
        <SessionRow
          v-for="session in monitor.filteredSessions"
          :key="session.session_id"
          :session="session"
          :blinking="isBlinking(session)"
          :blink-phase="monitor.blinkPhase"
          :is-new="monitor.newSessions.has(session.session_id)"
          @locate="locateWindow"
          @click="onSessionClick"
          @dblclick="onSessionDblClick"
        />
      </template>
      <template v-else>
        <div class="card-grid">
          <SessionCard
            v-for="session in monitor.filteredSessions"
            :key="session.session_id"
            :session="session"
            :blinking="isBlinking(session)"
            :blink-phase="monitor.blinkPhase"
            :is-new="monitor.newSessions.has(session.session_id)"
            @locate="locateWindow"
            @click="onSessionClick"
            @dblclick="onSessionDblClick"
          />
        </div>
      </template>
    </div>

    <SessionDetail
      v-model="showSessionDetail"
      :session="selectedSession"
      :can-acknowledge="selectedSession ? isBlinking(selectedSession) : false"
      @acknowledge="monitor.acknowledgeChange"
    />
    <PresetManager v-model="showPresetManager" />
    <AddWorkspace v-model="showAddWorkspace" />
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { getCurrentWindow } from '@tauri-apps/api/window'
import { LogicalSize } from '@tauri-apps/api/dpi'
import { useMonitorStore } from './stores/monitor.js'
import { useSettingsStore } from './stores/settings.js'
import { usePresetsStore } from './stores/presets.js'
import { useRefresh } from './composables/useRefresh.js'
import { api } from './api.js'
import TitleBar from './components/TitleBar.vue'
import SessionRow from './components/SessionRow.vue'
import SessionCard from './components/SessionCard.vue'
import SessionDetail from './components/SessionDetail.vue'
import PresetManager from './components/PresetManager.vue'
import AddWorkspace from './components/AddWorkspace.vue'

const monitor = useMonitorStore()
const settings = useSettingsStore()
const presets = usePresetsStore()
const appWindow = getCurrentWindow()

useRefresh()

const showPresetManager = ref(false)
const showAddWorkspace = ref(false)
const showSessionDetail = ref(false)
const selectedSession = ref(null)
const isHovering = ref(false)
const appOpacity = ref(0.3)

let flashTimer = null
let blinkTimer = null
let opacityTimer = null
let cleanupTimer = null

onMounted(() => {
  presets.load()
  setWindowOpacity(0.3)

  flashTimer = setInterval(() => {
    if (monitor.isFlashing) {
      monitor.doFlash()
      const opacity = monitor.flashCount % 2 === 1 ? 0.35 : 1.0
      setWindowOpacity(opacity)
    }
  }, 150)

  blinkTimer = setInterval(() => {
    if (monitor.isBlinking) {
      monitor.toggleBlink()
    }
  }, 500)
})

onUnmounted(() => {
  clearInterval(flashTimer)
  clearInterval(blinkTimer)
  clearTimeout(opacityTimer)
  clearTimeout(cleanupTimer)
})

function setWindowOpacity(opacity) {
  appOpacity.value = opacity
}

function isBlinking(session) {
  return monitor.changedSessions.has(session.session_id) || monitor.newSessions.has(session.session_id)
}

function locateWindow(pid) {
  if (!pid) return
  api.locateWindow(pid).catch(() => {})
}

function onSessionClick(session) {
  if (isBlinking(session)) {
    monitor.acknowledgeChange(session.session_id)
  }
}

function onSessionDblClick(session) {
  selectedSession.value = session
  showSessionDetail.value = true
}

function onAppClick() {
  if (monitor.isFlashing) {
    monitor.stopFlash()
    if (!isHovering.value) {
      setWindowOpacity(0.3)
    }
  }
  appWindow.setAlwaysOnTop(false).catch(() => {})
  scheduleCleanup()
}

function onMouseEnter() {
  isHovering.value = true
  if (!monitor.isFlashing) {
    setWindowOpacity(1.0)
    clearTimeout(opacityTimer)
  }
}

function onMouseLeave() {
  isHovering.value = false
  if (!monitor.isFlashing) {
    opacityTimer = setTimeout(() => {
      setWindowOpacity(0.3)
    }, 500)
  }
}

function scheduleCleanup() {
  const hasDead = monitor.sessions.some(s => !s.is_alive)
  if (hasDead && !cleanupTimer) {
    cleanupTimer = setTimeout(() => {
      monitor.hideDeadSessions()
      cleanupTimer = null
    }, 5000)
  }
}

function closeWindow() {
  appWindow.hide().catch(() => {})
}

function onToggleView() {
  settings.toggleViewMode()
}

watch(() => monitor.hasChanges, (hasChanges) => {
  if (hasChanges) {
    setWindowOpacity(1.0)
    clearTimeout(opacityTimer)
    monitor.startFlash()
    appWindow.setAlwaysOnTop(true).catch(() => {})
  } else {
    if (monitor.isFlashing) {
      monitor.stopFlash()
    }
    appWindow.setAlwaysOnTop(false).catch(() => {})
    if (!isHovering.value) {
      opacityTimer = setTimeout(() => setWindowOpacity(0.3), 500)
    }
  }
})

watch(() => settings.viewMode, (mode) => {
  if (mode === 'compact') {
    appWindow.setMinSize(new LogicalSize(200, 180)).catch(() => {})
    appWindow.setSize(new LogicalSize(260, 360)).catch(() => {})
  } else {
    appWindow.setMinSize(new LogicalSize(500, 400)).catch(() => {})
    appWindow.setSize(new LogicalSize(1100, 700)).catch(() => {})
  }
})
</script>

<style scoped>
.ccm-app {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}
.accent-line {
  height: 3px;
  background: linear-gradient(90deg, #6366f1, #8b5cf6, #a78bfa);
  flex-shrink: 0;
}
.content {
  flex: 1;
  overflow-y: auto;
  padding: 4px 6px;
}
.content.compact {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 8px;
}
.empty {
  text-align: center;
  padding: 40px 20px;
  color: var(--empty-text);
  font-size: 14px;
}
</style>
