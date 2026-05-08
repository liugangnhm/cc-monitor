<template>
  <div
    class="session-card"
    :class="{
      'is-new': isNew,
      'is-blinking': blinking && blinkPhase,
    }"
    @click="onClick"
    @dblclick="onDblClick"
  >
    <div class="strip" :class="{ 'is-new': isNew }" :style="{ background: accentColor }"></div>
    <div class="card-body">
      <div class="header">
        <div class="name">{{ projectName }}</div>
        <div class="actions">
          <div
            v-if="session.is_alive"
            class="locate-btn"
            @click.stop="onLocate"
          >&#x2B0D;</div>
          <div v-if="session.is_alive" class="badge" :class="session.status">
            {{ session.status === 'busy' ? '工作中' : '就绪' }}
          </div>
        </div>
      </div>
      <div class="separator"></div>
      <div class="tasks">
        <template v-if="session.tasks && session.tasks.length > 0">
          <div v-for="task in visibleTasks" :key="task.id" class="task-row">
            <div class="dot" :class="task.status"></div>
            <div class="task-text" :class="task.status">{{ task.subject }}</div>
          </div>
          <div v-if="session.tasks.length > 8" class="more">
            +{{ session.tasks.length - 8 }} 个任务
          </div>
        </template>
        <div v-else class="empty">暂无任务</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  session: { type: Object, required: true },
  blinking: { type: Boolean, default: false },
  blinkPhase: { type: Boolean, default: false },
  isNew: { type: Boolean, default: false },
})

const emit = defineEmits(['locate', 'click', 'dblclick'])

const projectName = computed(() => {
  return props.session.name || (props.session.cwd ? props.session.cwd.split(/[\\\\/]/).pop() : 'Unknown')
})

const accentColor = computed(() => {
  if (props.isNew) return 'var(--dot-done)'
  if (props.session.is_alive && props.session.status === 'busy') return 'var(--accent-busy)'
  if (props.session.is_alive) return 'var(--accent-idle)'
  return 'var(--accent-dead)'
})

const visibleTasks = computed(() => {
  return (props.session.tasks || []).slice(0, 8)
})

function onLocate() {
  emit('locate', props.session.pid)
}

function onClick() {
  emit('click', props.session)
}

function onDblClick() {
  emit('dblclick', props.session)
}
</script>

<style scoped>
.session-card {
  display: flex;
  cursor: pointer;
  border-radius: 4px;
  transition: background 0.2s;
}
.session-card.is-blinking .card-body {
  background: #fef9c3;
}
.session-card.is-blinking.is-new .card-body {
  background: #dcfce7;
}
.strip {
  width: 4px;
  border-radius: 2px 0 0 2px;
  flex-shrink: 0;
}
.strip.is-new {
  width: 6px;
}
.card-body {
  flex: 1;
  background: var(--card-bg);
  border-radius: 0 10px 10px 0;
  padding: 10px 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.name {
  font-size: 14px;
  font-weight: bold;
  color: var(--title);
  word-break: break-all;
  flex: 1;
}
.actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}
.locate-btn {
  font-size: 12px;
  color: #94a3b8;
  padding: 0 4px;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s;
}
.session-card:hover .locate-btn {
  opacity: 1;
}
.locate-btn:hover {
  color: var(--header-accent);
}
.badge {
  font-size: 11px;
  font-weight: bold;
  padding: 2px 10px;
  border-radius: 10px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.badge.busy {
  background: var(--badge-busy-bg);
  color: var(--badge-busy-text);
}
.badge.idle {
  background: var(--badge-idle-bg);
  color: var(--badge-idle-text);
}
.separator {
  height: 1px;
  background: var(--separator);
  margin: 8px 0;
}
.tasks {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.task-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.dot.completed { background: var(--dot-done); }
.dot.in_progress { background: var(--dot-active); }
.dot.pending { background: var(--dot-pending); }
.task-text {
  font-size: 13px;
  flex: 1;
  word-break: break-all;
}
.task-text.completed { color: var(--task-done-text); }
.task-text.in_progress { color: var(--task-text); }
.task-text.pending { color: var(--subtitle); }
.more {
  font-size: 12px;
  color: var(--subtitle);
}
.empty {
  font-size: 13px;
  color: var(--empty-text);
  text-align: center;
  padding: 8px 0;
}
</style>
