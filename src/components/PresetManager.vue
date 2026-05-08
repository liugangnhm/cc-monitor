<template>
  <el-dialog v-model="visible" title="预设管理" width="320px" align-center>
    <div class="preset-list">
      <div v-for="(preset, index) in presets" :key="preset.filepath" class="preset-item">
        <span class="name">{{ preset.name }}</span>
        <div class="actions">
          <el-button type="primary" link size="small" @click="onEdit(index)">编辑</el-button>
          <el-button type="danger" link size="small" @click="onDelete(index)">删除</el-button>
        </div>
      </div>
      <div v-if="presets.length === 0" class="empty">暂无预设</div>
    </div>
    <template #footer>
      <el-button type="primary" @click="onAdd">+ 添加预设</el-button>
    </template>
  </el-dialog>

  <PresetEdit
    v-model="showEdit"
    :preset="editingPreset"
    @save="onSave"
  />
</template>

<script setup>
import { computed, ref } from 'vue'
import { usePresetsStore } from '../stores/presets.js'
import { api } from '../api.js'
import PresetEdit from './PresetEdit.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue'])

const presetsStore = usePresetsStore()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const showEdit = ref(false)
const editingPreset = ref(null)

const presets = computed(() => presetsStore.presets)

function onAdd() {
  editingPreset.value = null
  showEdit.value = true
}

function onEdit(index) {
  editingPreset.value = presets.value[index]
  showEdit.value = true
}

async function onDelete(index) {
  const preset = presets.value[index]
  if (preset?.filepath) {
    await api.deletePreset(preset.filepath)
    await presetsStore.load()
  }
}

async function onSave() {
  await presetsStore.load()
  showEdit.value = false
}
</script>

<style scoped>
.preset-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.preset-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  background: var(--card-bg);
  border-radius: 6px;
}
.name {
  font-size: 13px;
  color: var(--title);
}
.actions {
  display: flex;
  gap: 4px;
}
.empty {
  text-align: center;
  padding: 20px;
  color: var(--empty-text);
  font-size: 13px;
}
</style>
