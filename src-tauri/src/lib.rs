mod data;
mod process;
mod window;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }

      #[cfg(desktop)]
      {
        use tauri::menu::{MenuBuilder, MenuItemBuilder};
        use tauri::tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
        use tauri::Manager;

        let show_i = MenuItemBuilder::with_id("show", "显示").build(app)?;
        let quit_i = MenuItemBuilder::with_id("quit", "退出").build(app)?;
        let menu = MenuBuilder::new(app).items(&[&show_i, &quit_i]).build()?;

        TrayIconBuilder::with_id("tray")
          .icon(app.default_window_icon().unwrap().clone())
          .menu(&menu)
          .on_menu_event(|app, event| match event.id().as_ref() {
            "show" => {
              if let Some(window) = app.get_webview_window("main") {
                let _ = window.unminimize();
                let _ = window.show();
                let _ = window.set_focus();
              }
            }
            "quit" => {
              app.exit(0);
            }
            _ => {}
          })
          .on_tray_icon_event(|tray, event| {
            if let TrayIconEvent::Click {
              button: MouseButton::Left,
              button_state: MouseButtonState::Up,
              ..
            } = event {
              let app = tray.app_handle();
              if let Some(window) = app.get_webview_window("main") {
                let _ = window.unminimize();
                let _ = window.show();
                let _ = window.set_focus();
              }
            }
          })
          .build(app)?;
      }

      Ok(())
    })
    .invoke_handler(tauri::generate_handler![
      data::load_sessions,
      data::load_tasks,
      data::is_process_alive,
      data::load_presets,
      data::save_preset,
      data::delete_preset,
      data::load_history,
      data::save_history,
      process::launch_session,
      process::find_executable,
      window::locate_window,
    ])
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
