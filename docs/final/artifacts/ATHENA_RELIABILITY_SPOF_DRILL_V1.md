# Athena Reliability / SPOF Drill V1

Purpose: keep MKM solo operations resilient while preserving Fact-Lock and HOLD guardrails.

## 1) SPOF map (single points of failure)

| Domain | Primary dependency | Failure signal | Immediate fallback | Recovery target |
|---|---|---|---|---|
| Power | local host power | host offline / scheduler not running | manual restart + task sanity check | < 30 min |
| Network | home ISP / router | no remote access | local execution path first, postpone cloud sync | < 60 min |
| Overlay access | Tailscale (or equivalent) | remote private route unavailable | local LAN / direct console path | < 30 min |
| NotebookLM push | `nlm` CLI + auth session | push task non-zero exit | keep local onefile as SSOT handoff | same day |
| Automation | Windows Task Scheduler | `LastTaskResult != 0` or stale run | manual run of builder/push scripts | same day |

Rule: if any SPOF is degraded, do not relax HOLD gate. Continue with observation-only outputs.

## 2) Monthly recovery drills (minimum set)

Run monthly (recommended first Sunday):

1. **Scheduler drill**
   - Verify tasks exist and are `Ready`.
   - Trigger once manually and confirm `LastTaskResult == 0`.

2. **Onefile rebuild drill**
   - Command:
   - `py "C:/workspace/scripts/build_athena_upload_onefile_latest.py"`
   - Check output file timestamp:
   - `docs/final/artifacts/ATHENA_UPLOAD_ONEFILE_LATEST.md`

3. **NotebookLM push drill**
   - Command:
   - `powershell -NoProfile -ExecutionPolicy Bypass -File "C:/workspace/scripts/Push-AthenaUploadOnefileToNotebooklm.ps1"`
   - Verify source title exists: `ATHENA_UPLOAD_ONEFILE_LATEST`

4. **HOLD lock integrity drill**
   - Confirm these keys still force HOLD:
   - `meta.high_reliability_decision`, `meta.price_output_locked`, `result.failed_reasons`

## 3) Reliability telemetry fields (add to daily report)

Append these operational fields to Athena daily summary:

- `automation.last_build_utc`
- `automation.last_push_utc`
- `automation.last_build_result` (0/1)
- `automation.last_push_result` (0/1)
- `automation.fail_count_24h`
- `automation.fail_count_7d`

Interpretation:
- Any non-zero result or rising fail count keeps mode conservative.
- Final action remains HOLD until failures are cleared and evidence is fresh.

## 4) Fixed close line

"현재 증거 범위에서는 운영 가능하나, Unverified Items 해소 전까지 HOLD 가드레일을 유지합니다."

