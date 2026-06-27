# Persona Diary Ops — Capacitor hypo shell v1

**`[HYPO]` · `research_only`** — App Store 출시·OS 앱 차단·Screen Time 실연동 **아님**.

## What it does

- WebView loads **`https://personadiary.com/ops`** (remote server URL in `capacitor.config.json`).
- Local `www/` is fallback redirect only.
- **Intent middleware** — deep link `personadiary://intent/save_moment_note?text=...` · share `ACTION_SEND` text/plain.
- **Offline ingest queue** — `personadiary_offline_ingest_queue_v1` in IndexedDB (Pull-first; no server upload).
- **No push** · **no server diary upload** · **SEND_GATE: HOLD** · **PD≠mkmlife payment**.

## Bootstrap (Windows · Android PoC · iOS scaffold)

From repo root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-PersonadiaryNativeShellHypoBootstrap_v1.ps1 -Platform Both
```

Copy contract + parity smoke (no simulator):

```powershell
py scripts\run_personadiary_native_shell_parity_smoke_v1.py --check-bootstrap --check-ios
```

**Non-prediction UX:** `docs/final/artifacts/personadiary_non_prediction_copy_contract_v1_latest.md` — Android·iOS **동일**; App Store·OS 제어 주장 금지.

## CLI — emulator + install + launch (Windows)

From repo root (starts AVD `Medium_Phone_API_36.1`, `gradlew installDebug`, launches app):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-PersonadiaryAndroidEmulatorRun_v1.ps1
```

Emulator already running (reinstall + relaunch):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-PersonadiaryAndroidEmulatorRun_v1.ps1 -SkipEmulatorStart
```

**System ANR (`Process system isn't responding`)** — API 36 preview + cold WebView load:

```powershell
# Kill emulator, cold boot, 4GB RAM, disable animations, reinstall APK
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-PersonadiaryAndroidEmulatorRun_v1.ps1 -KillRunningEmulator -ColdBoot
```

In the emulator dialog choose **Wait** (or rerun the command — script auto-taps Wait best-effort). If ANR persists: Android Studio → AVD Manager → **Wipe Data** on `Medium_Phone_API_36.1`, or create **API 35** AVD and pass `-AvdName`.

Validate artifact + screenshot:

```powershell
py scripts\run_personadiary_android_emulator_smoke_v1.py
```

One-shot invoke + validate:

```powershell
py scripts\run_personadiary_android_emulator_smoke_v1.py --invoke
```

Outputs: `reports/personadiary_android_emulator_run_latest.json`, `reports/personadiary_android_emulator_smoke_latest.png`, `reports/personadiary_android_emulator_smoke_latest.json`.

## Edge-to-edge (Android 15+ · P0)

- **Capacitor 6:** `MainActivity` → `WindowCompat.setDecorFitsSystemWindows(false)` + transparent status/nav bars.
- **Web ops:** `viewportFit: cover` + `--pd-safe-*` CSS (`var(--safe-area-inset-*, env(...))`).
- **Cap 7.1+ upgrade path:** `android.adjustMarginsForEdgeToEdge: "auto"` (not available on Cap 6).
- Smoke marker: `pd-android-edge-to-edge-v1` on `/ops`.

## Edge inset polish (P1)

- **Native:** `MainActivity` injects `WindowInsets` → `--safe-area-inset-*` on `documentElement` + black WebView background.
- **Web:** `PersonadiaryOpsEdgeBridge` adds `pd-ops-edge-body` / `pd-ops-edge-root` (deploy required for live `/ops`).
- **Smoke marker:** `pd-android-edge-insets-v1`
- **Emulator band probe:** `run_personadiary_android_emulator_smoke_v1.py` flags `#0a1210` body leak in screenshot bands (Pillow optional).

## Design tokens SSOT (Android ops · v1)

- JSON: `docs/final/artifacts/personadiary_android_design_tokens_v1_latest.json`
- Gate: `py scripts/check_personadiary_android_design_tokens_gate_v1.py` (exit 0)
- **Figma Design SSOT:** [PersonaDiary Android Ops v1](https://www.figma.com/design/O27IfEsEjltEe7uoD2zatC/PersonaDiary-Android-Ops-v1) · map `personadiary_figma_token_map_v1.json` · sync `py scripts/check_personadiary_figma_design_sync_gate_v1.py`
- CSS marker: `personadiary-android-design-tokens-v1` in `projects/no1kmedi/src/app/globals.css`

## Android Studio (optional GUI)

```powershell
cd projects\no1kmedi\personadiary-native-hypo-v1
npm run cap:open:android
```

WebView loads **`https://personadiary.com/ops`**. In app, confirm **네이티브·위생 [HYPO]** shows `runtime: capacitor_webview` when bridge detects Capacitor.

## Intent E2E (adb · research_only)

```powershell
py scripts\run_personadiary_android_intent_e2e_v1.py --invoke
py scripts\run_personadiary_android_intent_e2e_v1.py --invoke --skip-emulator-start --skip-install
```

Probes: `save_moment_note` · `add_reminder` · `share_text` → `reports/personadiary_android_intent_e2e_latest.json`

## iOS

Requires macOS + Xcode. Same `npm install` + `npx cap add ios` + `npx cap sync` on a Mac.

## SSOT

- Schema: `docs/final/schemas/personadiary_native_shell_hypo_v1.schema.json`
- Verify: `py scripts/verify_personadiary_native_shell_hypo_v1.py --check-bootstrap`
