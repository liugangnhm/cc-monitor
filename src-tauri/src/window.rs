#[cfg(target_os = "windows")]
use std::collections::HashSet;

#[cfg(target_os = "windows")]
type HWND = isize;
#[cfg(target_os = "windows")]
type LPARAM = isize;

#[cfg(target_os = "windows")]
#[link(name = "user32")]
extern "system" {
    fn AttachThreadInput(idAttach: u32, idAttachTo: u32, fAttach: i32) -> i32;
    fn EnumWindows(
        lpEnumFunc: Option<unsafe extern "system" fn(HWND, LPARAM) -> i32>,
        lParam: LPARAM,
    ) -> i32;
    fn GetForegroundWindow() -> HWND;
    fn GetWindowThreadProcessId(hwnd: HWND, lpdwProcessId: *mut u32) -> u32;
    fn IsWindow(hwnd: HWND) -> i32;
    fn SetForegroundWindow(hwnd: HWND) -> i32;
    fn ShowWindow(hwnd: HWND, nCmdShow: i32) -> i32;
}

#[cfg(target_os = "windows")]
#[link(name = "kernel32")]
extern "system" {
    fn GetCurrentThreadId() -> u32;
}

#[cfg(target_os = "windows")]
const SW_RESTORE: i32 = 9;

#[cfg(target_os = "windows")]
struct EnumData {
    target_pids: HashSet<u32>,
    results: Vec<HWND>,
}

#[cfg(target_os = "windows")]
unsafe extern "system" fn enum_callback(hwnd: HWND, lparam: LPARAM) -> i32 {
    let data = &mut *(lparam as *mut EnumData);
    if IsWindow(hwnd) != 0 {
        let mut proc_id = 0u32;
        GetWindowThreadProcessId(hwnd, &mut proc_id);
        if data.target_pids.contains(&proc_id) {
            data.results.push(hwnd);
        }
    }
    1
}

#[tauri::command]
pub fn locate_window(pid: u32) -> Result<(), String> {
    #[cfg(target_os = "windows")]
    {
        use sysinfo::{Pid, System};

        let mut candidate_pids = HashSet::new();
        candidate_pids.insert(pid);

        let s = System::new_all();

        // Collect parent and ancestors
        let mut current = Some(pid);
        while let Some(p) = current {
            let sys_pid = Pid::from(p as usize);
            if let Some(proc) = s.process(sys_pid) {
                if let Some(parent) = proc.parent() {
                    let parent_u32 = parent.as_u32();
                    candidate_pids.insert(parent_u32);
                    current = Some(parent_u32);
                } else {
                    current = None;
                }
            } else {
                current = None;
            }
        }

        // Collect children
        for (child_pid, child_proc) in s.processes() {
            if let Some(child_parent) = child_proc.parent() {
                if child_parent.as_u32() == pid {
                    candidate_pids.insert(child_pid.as_u32());
                }
            }
        }

        let mut data = EnumData {
            target_pids: candidate_pids,
            results: vec![],
        };

        unsafe {
            let _ = EnumWindows(Some(enum_callback), &mut data as *mut _ as LPARAM);
        }

        if let Some(&hwnd) = data.results.first() {
            unsafe {
                let _ = ShowWindow(hwnd, SW_RESTORE);
                let fg_hwnd = GetForegroundWindow();
                let fg_thread = GetWindowThreadProcessId(fg_hwnd, std::ptr::null_mut());
                let my_thread = GetCurrentThreadId();
                if fg_thread != my_thread {
                    let _ = AttachThreadInput(fg_thread, my_thread, 1);
                    let _ = SetForegroundWindow(hwnd);
                    let _ = AttachThreadInput(fg_thread, my_thread, 0);
                } else {
                    let _ = SetForegroundWindow(hwnd);
                }
            }
            Ok(())
        } else {
            Err("未找到窗口".to_string())
        }
    }

    #[cfg(not(target_os = "windows"))]
    {
        Err("窗口定位仅在 Windows 上可用".to_string())
    }
}
