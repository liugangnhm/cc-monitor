<template>
  <el-dialog
    v-model="visible"
    :title="projectName"
    width="300px"
    :show-close="true"
    :close-on-click-modal="true"
    align-center
  >
    <div class="detail-content">
      <div class="field"><span class="label">Session ID:</span><span class="value">{{ shortId }}</span></div>
      <div class="field"><span class="label">PID:</span><span class="value">{{ session?.pid }}</span></div>
      <div class="field"><span class="label">目录:</span><span class="value">{{ session?.cwd }}</span></div>
      <div class="field"><span class="label">状态:</span><span class="value">{{ statusLabel }}</span></div>
      <div class="field"><span class="label">存活:</span><span class="value">{{ session?.is_alive ? '是' : '否' }}</span></div>

      <template v-if="session?.tasks && session.tasks.length > 0">
        <el-divider />
        <div class="tasks-title">任务 ({{ session.tasks.length }})</div>
        <div v-for="task in session.tasks" :key="task.id" class="task-row">
          <div class="dot" :class="task.status"></div>
          <div class="task-text" :class="task.status">{{ task.subject }}</div>
        </div>
      </template>
    </div>

    <template #footer v-if="canAcknowledge">
      <el-button type="primary" @click="onAcknowledgeClick">确认变化</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  session: { type: Object, default: null },
  modelValue: { type: Boolean, default: false },
  canAcknowledge: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'acknowledge'])

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const projectName = computed(() => {
  if (!props.session) return ''
  return props.session.name || (props.session.cwd ? props.session.cwd.split(/[\\\\/]/).pop() : 'Unknown')
})

const shortId = computed(() => {
  if (!props.session) return ''
  return props.session.session_id.slice(0, 16) + '...'
})

const statusLabel = computed(() => {
  if (!props.session) return ''
  if (props.session.status === 'busy') return '工作中'
  if (props.session.status === 'idle') return '就绪'
  return props.session.status
})

function onAcknowledgeClick() {
  if (props.session) {
    emit('acknowledge', props.session.session_id)
  }
  visible.value = false
}
</script>

<style scoped>
.detail-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.field {
  display: flex;
  gap: 8px;
  font-size: 13px;
}
.label {
  color: var(--subtitle);
  flex-shrink: 0;
}
.value {
  color: var(--title);
  word-break: break-all;
}
.tasks-title {
  font-size: 14px;
  font-weight: bold;
  color: var(--title);
  margin-bottom: 8px;
}
.task-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}
.dot.completed { background: var(--dot-done); }
.dot.in_progress { background: var(--dot-active); }
.dot.pending { background: var(--dot-pending); }
.task-text {
  font-size: 13px;
  flex: 1;
}
.task-text.completed { color: var(--task-done-text); }
.task-text.in_progress { color: var(--task-text); }
.task-text.pending { color: var(--subtitle); }
</style>
