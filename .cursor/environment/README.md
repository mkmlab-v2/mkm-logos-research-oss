# Cursor Agent dev environment (MKM monorepo)

**SSOT:** `.cursor/environment.json` (Cursor resolves this before team/personal saved envs).

## What is committed

| File | Role |
| --- | --- |
| `../environment.json` | Cursor Cloud Agent config (`build` + `install`) |
| `Dockerfile` | Ubuntu 24.04 + git + Python 3 (no repo COPY) |
| `install.sh` | Idempotent `pip` + P0 path smoke on every VM boot |

## Dashboard (one-time)

1. Open [Cloud Agents → Environments](https://cursor.com/dashboard/cloud-agents#environments).
2. Connect GitHub/GitLab and select **this monorepo** (single root is enough for `projects/bitcoin-trading` work).
3. Cursor should pick up `.cursor/environment.json` from the branch you test.
4. **Secrets tab:** add only non-production keys (e.g. research APIs). Never paste live trading or VPS SSH secrets.
   - **Cloud Personal secrets hygiene:** prefer repo-scoped secrets for `mkmlab-v2/mkm-destiny-ai-41e38ec6` only; remove `OPENROUTER`/`GITHUB_TOKEN` from Cloud if unused. Never add `BINANCE_*`, `ENABLE_TRADING`, `NO1KMEDI_ADMIN_TOKEN`, or root `.env` copies.
5. **Update script (Dashboard, after onboarding):** `bash .cursor/environment/install.sh` — do not auto-start Next.js/payapp in Cloud.
6. Run a test Cloud Agent; confirm **Environment ready** and install log ends with `OK: P0/CONSTITUTION gate paths present`.

## Local verification (before pushing env changes)

```bash
python3 scripts/verify_p0_constitution_gate_paths_cloud_v1.py
py -m pytest tests/test_verify_p0_constitution_gate_paths_cloud_v1.py -q
```

Windows (local SSOT):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_p0_constitution_gate_paths.ps1
```

## Multi-repo

Default is **one clone = monorepo root**. Add extra repos in Dashboard only when a task truly spans repos (see `AGENTS.md` 도메인 핸드오프).

## /in-cloud (Cursor 3.7+)

| Use cloud (`/in-cloud`) | Keep local |
| --- | --- |
| Full Fact-Lock bundle · long pytest | `MISSION_LOG` · resume pack · checkpoint |
| B-track explore · CI fix PR (`/babysit`) | NotebookLM auth · DPAPI · `.env` |
| Large refactor / codebase search | Browser Tier 3 · ECC `athena_run_v1` |

SSOT matrix: `docs/final/artifacts/mkm_in_cloud_offload_matrix_v1_latest.json`

Onboard (steps 1–3): `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmCursor39Onboard_v1.ps1`

## Guardrails

`.cursor/rules/cursor-cloud-sandbox-boundary.mdc` · Changelog map: `projects/bitcoin-trading/ops/v2/CURSOR_CHANGELOG_INTEGRATION_PLAN_2026-03-24.md` §3.4.
