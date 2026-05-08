<template>
  <el-dialog
    v-model="visible"
    :title="isNew ? '添加预设' : '编辑预设'"
    width="420px"
    align-center
  >
    <el-form :model="form" label-width="140px" size="small">
      <el-form-item label="名称:">
        <el-input v-model="form.name" placeholder="预设名称" />
      </el-form-item>

      <el-divider />

      <el-form-item label="Auth Token:">
        <el-input v-model="form.token" type="password" show-password />
      </el-form-item>
      <el-form-item label="Base URL:">
        <el-input v-model="form.baseUrl" />
      </el-form-item>

      <el-divider />

      <el-form-item label="模型:">
        <el-input v-model="form.model" />
      </el-form-item>
      <el-form-item label="Sonnet 模型:">
        <el-input v-model="form.sonnet" />
      </el-form-item>
      <el-form-item label="Opus 模型:">
        <el-input v-model="form.opus" />
      </el-form-item>
      <el-form-item label="Haiku 模型:">
        <el-input v-model="form.haiku" />
      </el-form-item>
      <el-form-item label="Reasoning 模型:">
        <el-input v-model="form.reasoning" />
      </el-form-item>
      <el-form-item label="Subagent 模型:">
        <el-input v-model="form.subagent" />
      </el-form-item>

      <el-divider />

      <el-form-item label="API Timeout (ms):">
        <el-input v-model="form.timeout" />
      </el-form-item>
      <el-form-item label="权限模式:">
        <el-select v-model="form.permissionMode">
          <el-option label="bypassPermissions" value="bypassPermissions" />
          <el-option label="normal" value="normal" />
        </el-select>
      </el-form-item>

      <el-divider />

      <el-form-item label="插件 (每行一个):">
        <el-input v-model="form.plugins" type="textarea" :rows="3" />
      </el-form-item>

      <el-divider />

      <el-form-item label="其他 Settings JSON:">
        <el-input v-model="form.extra" type="textarea" :rows="3" />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button type="primary" @click="onSave">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { api } from '../api.js'

const props = defineProps({
  preset: { type: Object, default: null },
  modelValue: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'save'])

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const isNew = computed(() => !props.preset?.name)

const form = ref({
  name: '',
  token: '',
  baseUrl: '',
  model: '',
  sonnet: '',
  opus: '',
  haiku: '',
  reasoning: '',
  subagent: '',
  timeout: '3000000',
  permissionMode: 'bypassPermissions',
  plugins: '',
  extra: '{}',
})

watch(() => props.preset, (p) => {
  if (!p) {
    form.value = {
      name: '', token: '', baseUrl: '', model: '', sonnet: '', opus: '', haiku: '',
      reasoning: '', subagent: '', timeout: '3000000', permissionMode: 'bypassPermissions',
      plugins: '', extra: '{}',
    }
    return
  }
  const s = p.settings || {}
  const env = s.env || {}
  const perms = s.permissions || {}
  const plugs = s.enabledPlugins || {}

  form.value.name = p.name || ''
  form.value.token = env.ANTHROPIC_AUTH_TOKEN || ''
  form.value.baseUrl = env.ANTHROPIC_BASE_URL || ''
  form.value.model = env.ANTHROPIC_MODEL || ''
  form.value.sonnet = env.ANTHROPIC_DEFAULT_SONNET_MODEL || ''
  form.value.opus = env.ANTHROPIC_DEFAULT_OPUS_MODEL || ''
  form.value.haiku = env.ANTHROPIC_DEFAULT_HAIKU_MODEL || ''
  form.value.reasoning = env.ANTHROPIC_REASONING_MODEL || ''
  form.value.subagent = env.CLAUDE_CODE_SUBAGENT_MODEL || ''
  form.value.timeout = env.API_TIMEOUT_MS || '3000000'
  form.value.permissionMode = perms.defaultMode || 'bypassPermissions'
  form.value.plugins = Object.entries(plugs).filter(([, v]) => v).map(([k]) => k).join('\n')

  const extraSettings = { ...s }
  delete extraSettings.env
  delete extraSettings.permissions
  delete extraSettings.enabledPlugins
  delete extraSettings.statusLine
  delete extraSettings.skipDangerousModePermissionPrompt
  const extraEnv = { ...env }
  const knownEnv = [
    'ANTHROPIC_AUTH_TOKEN', 'ANTHROPIC_BASE_URL', 'ANTHROPIC_MODEL',
    'ANTHROPIC_DEFAULT_SONNET_MODEL', 'ANTHROPIC_DEFAULT_OPUS_MODEL',
    'ANTHROPIC_DEFAULT_HAIKU_MODEL', 'ANTHROPIC_REASONING_MODEL',
    'CLAUDE_CODE_SUBAGENT_MODEL', 'API_TIMEOUT_MS', 'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC',
  ]
  for (const k of knownEnv) delete extraEnv[k]
  if (Object.keys(extraEnv).length > 0) extraSettings.env = extraEnv
  form.value.extra = JSON.stringify(extraSettings, null, 2)
}, { immediate: true })

async function onSave() {
  const name = form.value.name.trim()
  if (!name) return

  let settings = {}
  try {
    settings = JSON.parse(form.value.extra)
    if (typeof settings !== 'object') settings = {}
  } catch {
    settings = {}
  }

  const env = settings.env || {}
  env.ANTHROPIC_AUTH_TOKEN = form.value.token.trim()
  env.ANTHROPIC_BASE_URL = form.value.baseUrl.trim()
  if (form.value.model.trim()) env.ANTHROPIC_MODEL = form.value.model.trim()
  if (form.value.sonnet.trim()) env.ANTHROPIC_DEFAULT_SONNET_MODEL = form.value.sonnet.trim()
  if (form.value.opus.trim()) env.ANTHROPIC_DEFAULT_OPUS_MODEL = form.value.opus.trim()
  if (form.value.haiku.trim()) env.ANTHROPIC_DEFAULT_HAIKU_MODEL = form.value.haiku.trim()
  if (form.value.reasoning.trim()) env.ANTHROPIC_REASONING_MODEL = form.value.reasoning.trim()
  if (form.value.subagent.trim()) env.CLAUDE_CODE_SUBAGENT_MODEL = form.value.subagent.trim()
  env.API_TIMEOUT_MS = form.value.timeout.trim() || '3000000'
  env.CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC = '1'
  settings.env = env

  settings.permissions = { defaultMode: form.value.permissionMode }

  const plugins = {}
  for (const line of form.value.plugins.split('\n')) {
    const pname = line.trim()
    if (pname) plugins[pname] = true
  }
  if (Object.keys(plugins).length > 0) {
    settings.enabledPlugins = plugins
  } else {
    delete settings.enabledPlugins
  }

  await api.savePreset(name, settings)

  if (props.preset?.filepath && props.preset.filepath !== `settings.json.${name}`) {
    await api.deletePreset(props.preset.filepath)
  }

  emit('save')
  visible.value = false
}
</script>
