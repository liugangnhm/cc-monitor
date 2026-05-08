<template>
  <div
    class="session-row"
    :class="{
      'is-new': isNew,
      'is-blinking': blinking && blinkPhase,
    }"
    @click="onClick"
    @dblclick="onDblClick"
  >
    <div class="strip" :class="{ 'is-new': isNew }" :style="{ background: accentColor }"></div>
    <div class="content">
      <div class="name">{{ projectName }}</div>
      <div class="status">{{ statusText }}</div>
      <div
        v-if="session.is_alive"
        class="locate-btn"
        @click.stop="onLocate"
      >&#x2B0D;</div>
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

const statusText = computed(() => {
  if (!props.session.is_alive) return '已结束 [0]'
  const badge = props.session.status === 'busy' ? '工作中' : '就绪'
  return `${badge} [${props.session.tasks?.length || 0}]`
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
.session-row {
  display: flex;
  align-items: center;
  height: 28px;
  cursor: pointer;
  border-radius: 4px;
  transition: background 0.2s;
}
.session-row.is-blinking {
  background: #fef9c3;
}
.session-row.is-blinking.is-new {
  background: #dcfce7;
}
.strip {
  width: 4px;
  height: 20px;
  border-radius: 2px;
  margin-right: 10px;
  flex-shrink: 0;
}
.strip.is-new {
  width: 6px;
}
.content {
  flex: 1;
  display: flex;
  align-items: center;
  min-width: 0;
  padding-right: 4px;
}
.name {
  flex: 1;
  font-size: 13px;
  color: var(--title);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.status {
  font-size: 12px;
  color: var(--status-text);
  flex-shrink: 0;
  margin-left: 8px;
}
.locate-btn {
  font-size: 12px;
  color: #94a3b8;
  padding: 0 4px;
  margin-left: 4px;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s;
  flex-shrink: 0;
}
.session-row:hover .locate-btn {
  opacity: 1;
}
.locate-btn:hover {
  color: var(--header-accent);
}
</style>
