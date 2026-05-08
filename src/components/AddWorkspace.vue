<template>
  <el-dialog v-model="visible" title="添加工作区" width="400px" align-center>
    <el-form :model="form" label-width="80px" size="small">
      <el-form-item label="工作区:">
        <el-select
          v-model="form.folder"
          filterable
          allow-create
          default-first-option
          placeholder="选择或输入文件夹路径"
          style="width: 100%"
        >
          <el-option
            v-for="ws in history"
            :key="ws"
            :label="ws"
            :value="ws"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="预设:">
        <el-select v-model="form.presetName" placeholder="选择预设" style="width: 100%">
          <el-option
            v-for="p in presets"
            :key="p.name"
            :label="p.name"
            :value="p.name"
          />
        </el-select>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="onConfirm">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { usePresetsStore } from '../stores/presets.js'
import { api } from '../api.js'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'confirm'])

const presetsStore = usePresetsStore()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const form = ref({
  folder: '',
  presetName: '',
})

const presets = computed(() => presetsStore.presets)
const history = ref([])

watch(visible, async (v) => {
  if (v) {
    history.value = await api.loadHistory()
    await presetsStore.load()
    if (presets.value.length > 0 && !form.value.presetName) {
      form.value.presetName = presets.value[0].name
    }
  }
})

async function onConfirm() {
  const folder = form.value.folder.trim()
  const presetName = form.value.presetName
  if (!folder || !presetName) return

  await api.launchSession(folder, presetName)
  emit('confirm')
  visible.value = false
}
</script>
