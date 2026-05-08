import { invoke } from '@tauri-apps/api/core'

export const api = {
  loadSessions: () => invoke('load_sessions'),
  loadTasks: (sessionId) => invoke('load_tasks', { sessionId }),
  isProcessAlive: (pid) => invoke('is_process_alive', { pid }),
  loadPresets: () => invoke('load_presets'),
  loadHistory: () => invoke('load_history'),
  saveHistory: (workspaces) => invoke('save_history', { workspaces }),
  launchSession: (folder, presetName) => invoke('launch_session', { folder, presetName }),
  findExecutable: (name) => invoke('find_executable', { name }),
  locateWindow: (pid) => invoke('locate_window', { pid }),
  savePreset: (name, settings) => invoke('save_preset', { name, settings }),
  deletePreset: (filepath) => invoke('delete_preset', { filepath }),
}
