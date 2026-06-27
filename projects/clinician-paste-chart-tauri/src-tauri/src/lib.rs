use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    Manager, WebviewUrl, WebviewWindowBuilder,
};
use tauri_plugin_clipboard_manager::ClipboardExt;
use tauri_plugin_global_shortcut::{GlobalShortcutExt, ShortcutState};

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

fn hotkey_binding() -> String {
    std::env::var("KM_CLINICIAN_HOTKEY").unwrap_or_else(|_| "Ctrl+Shift+V".to_string())
}

fn js_ascii_string_literal(text: &str) -> String {
    let mut out = String::from('"');
    for ch in text.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if c.is_ascii() && !c.is_control() => out.push(c),
            c => out.push_str(&format!("\\u{:04x}", c as u32)),
        }
    }
    out.push('"');
    out
}

fn build_paste_eval_js(text: &str) -> String {
    let encoded = js_ascii_string_literal(text);
    format!(
        r#"(function() {{
  const text = {encoded};
  function tryPaste(attempt) {{
    const el = document.querySelector(".pc-omni-textarea");
    if (el) {{
      const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
      setter.call(el, text);
      el.dispatchEvent(new Event("input", {{ bubbles: true }}));
      el.focus();
      return;
    }}
    if (attempt < 24) setTimeout(() => tryPaste(attempt + 1), 250);
  }}
  tryPaste(0);
}})();"#
    )
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

fn schedule_initial_clipboard_paste(app: &tauri::AppHandle) {
    let app_handle = app.clone();
    std::thread::spawn(move || {
        std::thread::sleep(std::time::Duration::from_millis(3500));
        let has_text = app_handle
            .clipboard()
            .read_text()
            .ok()
            .is_some_and(|t| !t.trim().is_empty());
        if has_text {
            paste_clipboard_into_chart(&app_handle);
        }
    });
}

fn paste_clipboard_into_chart(app: &tauri::AppHandle) {
    show_main_window(app);
    let app_handle = app.clone();
    std::thread::spawn(move || {
        let text = match app_handle.clipboard().read_text() {
            Ok(value) if !value.trim().is_empty() => value,
            _ => return,
        };
        let js = build_paste_eval_js(&text);
        let eval_app = app_handle.clone();
        let _ = app_handle.run_on_main_thread(move || {
            if let Some(win) = eval_app.get_webview_window("main") {
                let _ = win.eval(&js);
            }
        });
    });
}

fn register_paste_hotkey(app: &tauri::AppHandle) {
    let binding = hotkey_binding();
    app.global_shortcut()
        .on_shortcut(binding.as_str(), |triggered_app, _shortcut, event| {
            if event.state != ShortcutState::Pressed {
                return;
            }
            paste_clipboard_into_chart(triggered_app);
        })
        .expect("failed to register KM_CLINICIAN_HOTKEY");
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let _ = dotenvy::dotenv();

    tauri::Builder::default()
        .plugin(tauri_plugin_clipboard_manager::init())
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .setup(|app| {
            let paste_i = MenuItem::with_id(app, "paste", "클립보드 붙여넣기", true, None::<&str>)?;
            let open_i = MenuItem::with_id(app, "open", "Paste Chart 열기", true, None::<&str>)?;
            let quit_i = MenuItem::with_id(app, "quit", "종료", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&paste_i, &open_i, &quit_i])?;

            let app_handle = app.handle().clone();
            TrayIconBuilder::new()
                .menu(&menu)
                .tooltip("MKM Paste Chart")
                .on_menu_event(move |app, event| match event.id.as_ref() {
                    "paste" => paste_clipboard_into_chart(app),
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

            register_paste_hotkey(&app_handle);
            show_main_window(&app_handle);
            schedule_initial_clipboard_paste(&app_handle);
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
