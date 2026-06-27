# Logos Research Studio — Capacitor hypo shell v1

**`[HYPO]` · `research_only`** — App Store 출시·푸시·오프라인 큐 **아님**.

## What it does

- WebView loads **`https://logos.jema-ai.com/logos-research/studio`** (remote server URL in `capacitor.config.json`).
- Local `www/` is fallback redirect only.
- Curated preset Graph Studio — **not** open LLM for arbitrary questions.
- **SEND_GATE: HOLD** · artifact: `docs/final/artifacts/logos_research_mobile_shell_hypo_v1_latest.json`

## Bootstrap (Windows · Android PoC)

From repo root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-LogosResearchNativeShellHypoBootstrap_v1.ps1 -Platform Android
```

Parity smoke (no emulator):

```powershell
py scripts/check_logos_research_capacitor_shell_hypo_v1.py
```
