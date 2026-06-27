# MKM Paste Chart — Tauri P2 (scaffold)

Desktop shell for [Paste Chart v1](https://app.jema-ai.com/clinician?panel=gold). Loads the hosted clinician workspace in a native webview (Entry A). **Track B · research_only · human_confirm.**

## Prerequisites

- [Rust](https://rustup.rs/) (stable)
- Node.js 20+
- Windows: WebView2 (usually preinstalled on Win10+)
- Windows build: VS Build Tools 2022 (C++ workload)

## Setup

```powershell
cd C:\workspace\projects\clinician-paste-chart-tauri
copy .env.example .env
# Edit .env — set KM_CLINICIAN_EMAIL (Pro allowlist on server)
npm install
```

## Run (dev)

```powershell
# MSVC env + .env
powershell -File C:\workspace\scripts\Invoke-ClinicianPasteChartTauriDev_v1.ps1
```

Tray: 좌클릭 또는 「Paste Chart 열기」로 창 표시.

### P2.2 — global hotkey + clipboard paste

- Default hotkey: **Ctrl+Shift+V** (`KM_CLINICIAN_HOTKEY` to override)
- Action: show window → read system clipboard → inject into `.pc-omni-textarea` (React controlled input)
- Tray menu: **클립보드 붙여넣기**

## Check (Rust only)

```powershell
npm run check:rust
```

## Build

```powershell
# MSVC required — portable exe + NSIS installer
npm run build
npm run smoke:build-artifact
npm run smoke:nsis-artifact
```

## Scaffold smoke (no Rust required)

```powershell
npm run smoke:scaffold
npm run smoke:p22
```

## Env

| Variable | Purpose |
|----------|---------|
| `KM_CLINICIAN_EMAIL` | Appended as `?email=` for Pro gate + API headers |
| `KM_CLINICIAN_HOTKEY` | Global shortcut (default `Ctrl+Shift+V`) |
| `KM_CLINICIAN_PASTE_CHART_URL` | Base URL (default prod gold panel) |

Sync VPS allowlist + LLM keys: `powershell -File C:\workspace\scripts\Sync-No1kmediClinicianOpsEnvToVps_v1.ps1`
