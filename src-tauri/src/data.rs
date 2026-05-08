use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Task {
    pub id: String,
    pub subject: String,
    pub status: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Session {
    pub pid: u32,
    pub session_id: String,
    pub cwd: String,
    pub name: Option<String>,
    pub status: String,
    pub is_alive: bool,
    pub tasks: Vec<Task>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Preset {
    pub name: String,
    pub cli_args: Vec<String>,
    pub settings: serde_json::Value,
    pub filepath: String,
}

fn claude_dir() -> PathBuf {
    dirs::home_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join(".claude")
}

#[tauri::command]
pub fn is_process_alive(pid: u32) -> bool {
    if pid == 0 {
        return false;
    }
    use sysinfo::{Pid, ProcessesToUpdate, System};
    let mut s = System::new();
    let pid = Pid::from(pid as usize);
    s.refresh_processes(ProcessesToUpdate::Some(&[pid]), false);
    s.process(pid).is_some()
}

pub fn load_tasks_raw(session_id: &str) -> Vec<Task> {
    let tasks_dir = claude_dir().join("tasks").join(session_id);
    if !tasks_dir.exists() {
        return vec![];
    }
    let mut tasks = vec![];
    if let Ok(entries) = fs::read_dir(tasks_dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.extension().and_then(|e| e.to_str()) != Some("json") {
                continue;
            }
            let data: serde_json::Value = match fs::read_to_string(&path)
                .ok()
                .and_then(|s| serde_json::from_str(&s).ok())
            {
                Some(v) => v,
                None => continue,
            };
            tasks.push(Task {
                id: data
                    .get("id")
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .to_string(),
                subject: data
                    .get("subject")
                    .and_then(|v| v.as_str())
                    .unwrap_or("未知任务")
                    .to_string(),
                status: data
                    .get("status")
                    .and_then(|v| v.as_str())
                    .unwrap_or("pending")
                    .to_string(),
            });
        }
    }
    tasks
}

#[tauri::command]
pub fn load_tasks(session_id: String) -> Vec<Task> {
    load_tasks_raw(&session_id)
}

#[tauri::command]
pub fn load_sessions() -> Vec<Session> {
    let sessions_dir = claude_dir().join("sessions");
    if !sessions_dir.exists() {
        return vec![];
    }
    let mut sessions = vec![];
    if let Ok(entries) = fs::read_dir(sessions_dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.extension().and_then(|e| e.to_str()) != Some("json") {
                continue;
            }
            let data: serde_json::Value = match fs::read_to_string(&path)
                .ok()
                .and_then(|s| serde_json::from_str(&s).ok())
            {
                Some(v) => v,
                None => continue,
            };
            let pid = data.get("pid").and_then(|v| v.as_u64()).unwrap_or(0) as u32;
            let is_alive = if pid > 0 { is_process_alive(pid) } else { false };
            let session_id = data
                .get("sessionId")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string();
            let tasks = if !session_id.is_empty() {
                load_tasks_raw(&session_id)
            } else {
                vec![]
            };
            let cwd = data
                .get("cwd")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string();
            let name = data
                .get("name")
                .and_then(|v| v.as_str())
                .map(|s| s.to_string());
            let status = data
                .get("status")
                .and_then(|v| v.as_str())
                .unwrap_or("idle")
                .to_string();

            sessions.push(Session {
                pid,
                session_id,
                cwd,
                name,
                status,
                is_alive,
                tasks,
            });
        }
    }
    sessions
}

fn history_file() -> PathBuf {
    claude_dir().join("cc-monitor").join("history.json")
}

#[tauri::command]
pub fn load_history() -> Vec<String> {
    let path = history_file();
    if !path.exists() {
        return vec![];
    }
    let data: serde_json::Value = match fs::read_to_string(&path)
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
    {
        Some(v) => v,
        None => return vec![],
    };
    data.get("workspaces")
        .and_then(|v| v.as_array())
        .map(|arr| {
            arr.iter()
                .filter_map(|v| v.as_str().map(|s| s.to_string()))
                .collect()
        })
        .unwrap_or_default()
}

#[tauri::command]
pub fn save_history(workspaces: Vec<String>) {
    let path = history_file();
    if let Some(parent) = path.parent() {
        let _ = fs::create_dir_all(parent);
    }
    let data = serde_json::json!({ "workspaces": workspaces });
    let _ = fs::write(
        &path,
        serde_json::to_string_pretty(&data).unwrap_or_default(),
    );
}

#[tauri::command]
pub fn load_presets() -> Vec<Preset> {
    let dir = claude_dir();
    let mut presets = vec![];
    if !dir.exists() {
        return presets;
    }
    let mut entries: Vec<_> = match fs::read_dir(&dir) {
        Ok(r) => r.flatten().collect(),
        Err(_) => return presets,
    };
    entries.sort_by_key(|e| e.file_name());
    for entry in entries {
        let filename = entry.file_name();
        let filename = match filename.to_str() {
            Some(s) => s,
            None => continue,
        };
        if !filename.starts_with("settings.json.") || filename == "settings.json" {
            continue;
        }
        let filepath = entry.path();
        if !filepath.is_file() {
            continue;
        }
        let name = filename["settings.json.".len()..].to_string();
        if name.is_empty() {
            continue;
        }
        let settings: serde_json::Value = match fs::read_to_string(&filepath)
            .ok()
            .and_then(|s| serde_json::from_str(&s).ok())
        {
            Some(v) => v,
            None => continue,
        };
        presets.push(Preset {
            name,
            cli_args: vec![
                "--allow-dangerously-skip-permissions".to_string(),
                "--settings".to_string(),
                filepath.to_string_lossy().to_string(),
            ],
            settings,
            filepath: filepath.to_string_lossy().to_string(),
        });
    }
    presets
}

#[tauri::command]
pub fn save_preset(name: String, settings: serde_json::Value) {
    let filepath = claude_dir().join(format!("settings.json.{}", name));
    let _ = fs::write(
        &filepath,
        serde_json::to_string_pretty(&settings).unwrap_or_default(),
    );
}

#[tauri::command]
pub fn delete_preset(filepath: String) {
    let path = PathBuf::from(filepath);
    if path.exists() {
        let _ = fs::remove_file(path);
    }
}
