<template>
  <div class="title-bar" data-tauri-drag-region @mousedown="startDrag">
    <div class="title" data-tauri-drag-region>CCM</div>
    <div class="spacer"></div>
    <div class="task-count" v-if="totalTasks > 0">{{ totalTasks }} 任务</div>
    <div class="btn" @click.stop="emit('settings')" @mousedown.stop>&#x2699;</div>
    <div class="btn add" @click.stop="emit('add')" @mousedown.stop>+</div>
    <div class="btn" @click.stop="emit('toggleView')" @mousedown.stop>{{ viewMode === 'compact' ? '&#x229E;' : '&#x2261;' }}</div>
    <div class="btn close" @click.stop="emit('close')" @mousedown.stop>&#x00D7;</div>
  </div>
</template>

<script setup>
import { getCurrentWindow } from '@tauri-apps/api/window'

defineProps({
  totalTasks: { type: Number, default: 0 },
  viewMode: { type: String, default: 'compact' },
})
const emit = defineEmits(['settings', 'add', 'toggleView', 'close'])

const appWindow = getCurrentWindow()

function startDrag() {
  appWindow.startDragging().catch(() => {})
}
</script>

<style scoped>
.title-bar {
  height: 40px;
  display: flex;
  align-items: center;
  padding: 0 12px;
  background: var(--header-bg);
  border-bottom: 1px solid #e2e8f0;
  user-select: none;
}
.title {
  font-size: 14px;
  font-weight: bold;
  color: var(--header-title);
}
.spacer {
  flex: 1;
}
.task-count {
  font-size: 12px;
  color: var(--status-text);
  margin-right: 8px;
}
.btn {
  font-size: 14px;
  color: var(--status-text);
  padding: 0 6px;
  cursor: pointer;
  transition: color 0.2s;
}
.btn.add {
  color: var(--header-accent);
  font-weight: bold;
  font-size: 16px;
}
.btn.close {
  padding: 0 8px;
  font-size: 18px;
}
.btn:hover {
  color: var(--title);
}
</style>
