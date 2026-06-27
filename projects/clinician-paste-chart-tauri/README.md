# MKM Paste Chart — Tauri P2 (scaffold)

Desktop shell for [Paste Chart v1](https://app.jema-ai.com/clinician?panel=gold). Loads the hosted clinician workspace in a native webview (Entry A). **Track B · research_only · human_confirm.**

## Prerequisites

- [Rust](https://rustup.rs/) (stable)
- Node.js 20+
- Windows: WebView2 (usually preinstalled on Win10+)

## Setup

```powershell
cd C:\workspace\projects\clinician-paste-chart-tauri
copy .env.example .env
# Edit .env — set KM_CLINICIAN_EMAIL (Pro allowlist on server)
npm install
```

## Run (dev)

```powershell
# .env with KM_CLINICIAN_EMAIL (see .env.example)
npm run dev
```

Tray: 좌클릭 또는 「Paste Chart 열기」로 창 표시.

## Check (Rust only)

```powershell
npm run check:rust
```

## Build

```powershell
npm run build
```

## Scaffold smoke (no Rust required)

```powershell
npm run smoke:scaffold
```

## Env

| Variable | Purpose |
|----------|---------|
| `KM_CLINICIAN_EMAIL` | Appended as `?email=` for Pro gate + API headers |
| `KM_CLINICIAN_PASTE_CHART_URL` | Base URL (default prod gold panel) |

Sync VPS allowlist + LLM keys: `powershell -File C:\workspace\scripts\Sync-No1kmediClinicianOpsEnvToVps_v1.ps1`
