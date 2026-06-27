use tauri::{WebviewUrl, WebviewWindowBuilder};

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

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let start_url = build_start_url();
    let parsed = start_url
        .parse()
        .expect("KM_CLINICIAN_PASTE_CHART_URL must be a valid http(s) URL");

    tauri::Builder::default()
        .setup(move |app| {
            WebviewWindowBuilder::new(app, "main", WebviewUrl::External(parsed))
                .title("MKM Paste Chart")
                .inner_size(1280.0, 860.0)
                .build()?;
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
