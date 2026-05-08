use std::env;
use std::process::Command;

const EXTRA_SEARCH_PATHS: &[&str] = &[".local/bin", ".", "bin"];

pub fn find_executable_raw(name: &str) -> Option<String> {
    if let Ok(path_var) = env::var("PATH") {
        for dir in env::split_paths(&path_var) {
            let candidate = dir.join(name);
            if candidate.is_file() {
                return Some(candidate.to_string_lossy().to_string());
            }
            #[cfg(target_os = "windows")]
            for suffix in [".exe", ".cmd", ".bat"] {
                let candidate_with_ext = dir.join(format!("{}{}", name, suffix));
                if candidate_with_ext.is_file() {
                    return Some(candidate_with_ext.to_string_lossy().to_string());
                }
            }
        }
    }
    if let Some(home) = dirs::home_dir() {
        for sub in EXTRA_SEARCH_PATHS {
            let dir = home.join(sub);
            if !dir.is_dir() {
                continue;
            }
            let candidate = dir.join(name);
            if candidate.is_file() {
                return Some(candidate.to_string_lossy().to_string());
            }
            #[cfg(target_os = "windows")]
            for suffix in [".exe", ".cmd", ".bat"] {
                let candidate_with_ext = dir.join(format!("{}{}", name, suffix));
                if candidate_with_ext.is_file() {
                    return Some(candidate_with_ext.to_string_lossy().to_string());
                }
            }
        }
    }
    None
}

#[tauri::command]
pub fn find_executable(name: String) -> Option<String> {
    find_executable_raw(&name)
}

#[tauri::command]
pub fn launch_session(folder: String, preset_name: String) -> Result<(), String> {
    let presets = crate::data::load_presets();
    let preset = presets
        .into_iter()
        .find(|p| p.name == preset_name)
        .ok_or_else(|| "预设不存在".to_string())?;

    let claude_path =
        find_executable_raw("claude").ok_or("找不到 claude 可执行文件")?;
    let pwsh_path = find_executable_raw("pwsh")
        .or_else(|| find_executable_raw("pwsh.exe"))
        .or_else(|| find_executable_raw("powershell"))
        .or_else(|| find_executable_raw("powershell.exe"))
        .ok_or("找不到 PowerShell")?;

    let title = format!(
        "{} - {}",
        std::path::Path::new(&folder)
            .file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("Unknown"),
        preset.name
    );

    let quoted_args: String = preset
        .cli_args
        .iter()
        .map(|a| format!("'{}'", a.replace("'", "''")))
        .collect::<Vec<_>>()
        .join(" ");
    let ps_cmd = format!("& '{}' {}", claude_path.replace("'", "''"), quoted_args);

    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NEW_CONSOLE: u32 = 0x00000010;

        if let Some(wt_path) =
            find_executable_raw("wt").or_else(|| find_executable_raw("wt.exe"))
        {
            let _ = Command::new(&wt_path)
                .args([
                    "-w",
                    "-1",
                    "--title",
                    &title,
                    "--suppressApplicationTitle",
                    "--",
                    &pwsh_path,
                    "-NoExit",
                    "-WorkingDirectory",
                    &folder,
                    "-Command",
                    &ps_cmd,
                ])
                .creation_flags(CREATE_NEW_CONSOLE)
                .spawn();
        } else {
            let cmd = format!(
                r#"$Host.UI.RawUI.WindowTitle = "{title}"; chcp 65001 > $null; [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Set-Location '{folder}'; {ps_cmd}"#
            );
            let _ = Command::new(&pwsh_path)
                .args(["-NoExit", "-Command", &cmd])
                .creation_flags(CREATE_NEW_CONSOLE)
                .spawn();
        }
    }

    #[cfg(not(target_os = "windows"))]
    {
        let _ = Command::new(&pwsh_path)
            .args(["-NoExit", "-WorkingDirectory", &folder, "-Command", &ps_cmd])
            .spawn();
    }

    let mut history = crate::data::load_history();
    if let Some(pos) = history.iter().position(|h| h == &folder) {
        history.remove(pos);
    }
    history.insert(0, folder);
    history.truncate(20);
    crate::data::save_history(history);

    Ok(())
}
