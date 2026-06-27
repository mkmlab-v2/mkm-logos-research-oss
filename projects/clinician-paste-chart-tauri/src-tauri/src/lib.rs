use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    Manager, WebviewUrl, WebviewWindowBuilder,
};

fn build_start_url() -> String {
    let base = std::env::var("KM_CLINICIAN_PASTE_CHART_URL").unwrap_or_else(|_| {
        "https://app.jema-ai.com/clinician?panel=gold".to_string()
    });
    let email = std::env::var("KM_CLINICIAN_EMAIL")
        .unwrap_or_default()
        .trim()
        .to_lowercase();
    if email.is_empty() {
        return base;
    }
    let sep = if base.contains('?') { '&' } else { '?' };
    format!("{base}{sep}email={}", urlencoding::encode(&email))
}

fn show_main_window(app: &tauri::AppHandle) {
    if let Some(win) = app.get_webview_window("main") {
        let _ = win.show();
        let _ = win.unminimize();
        let _ = win.set_focus();
        return;
    }
    let start_url = build_start_url();
    let parsed = start_url
        .parse()
        .expect("KM_CLINICIAN_PASTE_CHART_URL must be a valid http(s) URL");
    let _ = WebviewWindowBuilder::new(app, "main", WebviewUrl::External(parsed))
        .title("MKM Paste Chart")
        .inner_size(1280.0, 860.0)
        .build();
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let _ = dotenvy::dotenv();

    tauri::Builder::default()
        .setup(|app| {
            let open_i = MenuItem::with_id(app, "open", "Paste Chart 열기", true, None::<&str>)?;
            let quit_i = MenuItem::with_id(app, "quit", "종료", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&open_i, &quit_i])?;

            let app_handle = app.handle().clone();
            TrayIconBuilder::new()
                .menu(&menu)
                .tooltip("MKM Paste Chart")
                .on_menu_event(move |app, event| match event.id.as_ref() {
                    "open" => show_main_window(app),
                    "quit" => app.exit(0),
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        show_main_window(tray.app_handle());
                    }
                })
                .build(app)?;

            show_main_window(&app_handle);
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
