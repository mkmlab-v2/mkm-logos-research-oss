Task snapshot (raw):

Folder: \
HostName:                             DESKTOP-2511
TaskName:                             \Bitcoin-Ops-Phase1-Chain-Daily
Next Run Time:                        2026-04-07 오전 8:30:00
Status:                               Ready
Logon Mode:                           Interactive only
Last Run Time:                        2026-04-06 오후 9:18:57
Last Result:                          1
Author:                               DESKTOP-2511\PRO
Task To Run:                          powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\run_ops_phase1_chain.ps1 -IncludeConstitutionGates -Strict
Start In:                             N/A
Comment:                              N/A
Scheduled Task State:                 Enabled
Idle Time:                            Disabled
Power Management:                     Stop On Battery Mode, No Start On Batteries
Run As User:                          PRO
Delete Task If Not Rescheduled:       Disabled
Stop Task If Runs X Hours and X Mins: 72:00:00
Schedule:                             Scheduling data is not available in this format.
Schedule Type:                        Daily 
Start Time:                           오전 8:30:00
Start Date:                           2026-04-06
End Date:                             N/A
Days:                                 Every 1 day(s)
Months:                               N/A
Repeat: Every:                        Disabled
Repeat: Until: Time:                  Disabled
Repeat: Until: Duration:              Disabled
Repeat: Stop If Still Running:        Disabled


ops_phase1_readiness_latest.json:
{
    "schema":  "ops_phase1_readiness_v1",
    "ts_utc":  "2026-04-06T11:02:24.5436293+00:00",
    "runner":  "verify_ops_phase1_operational_readiness.ps1",
    "strict":  false,
    "all_ok":  true,
    "checks":  [
                   {
                       "id":  "task_exists",
                       "ok":  true,
                       "detail":  "\\Bitcoin-Ops-Phase1-Chain-Daily"
                   },
                   {
                       "id":  "task_to_run",
                       "ok":  true,
                       "detail":  "powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\\workspace\\projects\\bitcoin-trading\\ops\\windows-rehearsal\\run_ops_phase1_chain.ps1 -IncludeConstitutionGates -Strict"
                   },
                   {
                       "id":  "task_strict_mode_enabled",
                       "ok":  true,
                       "detail":  "strict_flag_present"
                   },
                   {
                       "id":  "logon_mode",
                       "ok":  true,
                       "detail":  "Interactive only",
                       "note":  "Interactive only = may not run when logged off; set Run whether user is logged on if unattended required."
                   },
                   {
                       "id":  "last_run_time",
                       "ok":  true,
                       "detail":  "2026-04-06 오후 7:59:08"
                   },
                   {
                       "id":  "last_result",
                       "ok":  true,
                       "detail":  "1"
                   },
                   {
                       "id":  "last_result_gate",
                       "ok":  false,
                       "detail":  "1"
                   },
                   {
                       "id":  "ops_alarm_webhook_url",
                       "ok":  true,
                       "detail":  "set"
                   },
                   {
                       "id":  "phase1_report_fresh",
                       "ok":  true,
                       "detail":  "age_hours=0.03 max=30"
                   },
                   {
                       "id":  "last_result_gate_override",
                       "ok":  true,
                       "detail":  "phase1_report_overrides_nonzero_last_result"
                   }
               ]
}

all_green_latest.json:
{
    "schema":  "verify_all_green_v1",
    "ts_utc":  "2026-04-06T12:16:29.6904009+00:00",
    "enforce_registry":  false,
    "overall_ok":  true,
    "steps":  [
                  {
                      "step":  "ensure_public_event_gateway",
                      "exit_code":  0,
                      "ok":  true
                  },
                  {
                      "step":  "verify_fused_quant_pixel_runtime_health",
                      "exit_code":  0,
                      "ok":  true
                  },
                  {
                      "step":  "verify_jemaai_showroom_deploy",
                      "exit_code":  0,
                      "ok":  true
                  },
                  {
                      "step":  "verify_ops_fusion_cycle_status",
                      "exit_code":  0,
                      "ok":  true
                  },
                  {
                      "step":  "reconcile_automation_registry",
                      "exit_code":  0,
                      "ok":  true
                  }
              ]
}

automation_registry_reconcile_latest.json:
{
    "schema":  "automation_registry_reconcile_v1",
    "ts_utc":  "2026-04-06T12:16:29.6408715+00:00",
    "registry_path":  "C:\\workspace\\projects\\bitcoin-trading\\ops\\windows-rehearsal\\automation_registry.json",
    "enforce":  false,
    "all_ok":  true,
    "drift_count":  0,
    "critical_drift_count":  0,
    "fixed_count":  0,
    "ignore_execution_health":  false,
    "execution_issue_count":  0,
    "execution_critical_issue_count":  0,
    "items":  [
                  {
                      "task_name":  "\\Bitcoin-Fused-QuantPixel-SOP-Strict-Check",
                      "expected_status":  "Ready",
                      "actual_status":  "Ready",
                      "exists":  true,
                      "drift":  false,
                      "enforce_action":  "none",
                      "enforce_ok":  null,
                      "owner":  "runtime",
                      "criticality":  "critical",
                      "next_run_time":  "2026-04-07 오전 9:15:00",
                      "last_result":  "0",
                      "execution_healthy":  true
                  },
                  {
                      "task_name":  "\\Bitcoin-Fused-QuantPixel-SOP-Live-Daily",
                      "expected_status":  "Ready",
                      "actual_status":  "Ready",
                      "exists":  true,
                      "drift":  false,
                      "enforce_action":  "none",
                      "enforce_ok":  null,
                      "owner":  "runtime",
                      "criticality":  "critical",
                      "next_run_time":  "2026-04-07 오전 9:35:00",
                      "last_result":  "0",
                      "execution_healthy":  true
                  },
                  {
                      "task_name":  "\\Bitcoin-Public-Event-Recovery-10min",
                      "expected_status":  "Ready",
                      "actual_status":  "Ready",
                      "exists":  true,
                      "drift":  false,
                      "enforce_action":  "none",
                      "enforce_ok":  null,
                      "owner":  "showroom",
                      "criticality":  "critical",
                      "next_run_time":  "2026-04-06 오후 9:20:00",
                      "last_result":  "0",
                      "execution_healthy":  true
                  },
                  {
                      "task_name":  "\\Bitcoin-KPI-Snapshot-5min",
                      "expected_status":  "Ready",
                      "actual_status":  "Ready",
                      "exists":  true,
                      "drift":  false,
                      "enforce_action":  "none",
                      "enforce_ok":  null,
                      "owner":  "runtime",
                      "criticality":  "high",
                      "next_run_time":  "2026-04-06 오후 9:18:00",
                      "last_result":  "0",
                      "execution_healthy":  true
                  },
                  {
                      "task_name":  "\\Bitcoin-Guardrails-Fast-Verify-30min",
                      "expected_status":  "Ready",
                      "actual_status":  "Ready",
                      "exists":  true,
                      "drift":  false,
                      "enforce_action":  "none",
                      "enforce_ok":  null,
                      "owner":  "runtime",
                      "criticality":  "high",
                      "next_run_time":  "2026-04-06 오후 9:32:00",
                      "last_result":  "0",
                      "execution_healthy":  true
                  },
                  {
                      "task_name":  "\\Bitcoin-Ops-Fusion-Cycle-Auto",
                      "expected_status":  "Ready",
                      "actual_status":  "Ready",
                      "exists":  true,
                      "drift":  false,
                      "enforce_action":  "none",
                      "enforce_ok":  null,
                      "owner":  "ops_fusion",
                      "criticality":  "high",
                      "next_run_time":  "2026-04-06 오후 10:05:00",
                      "last_result":  "0",
                      "execution_healthy":  true
                  },
                  {
                      "task_name":  "\\Bitcoin-WaitingQueue-BTCBinance-Daily-Strict",
                      "expected_status":  "Ready",
                      "actual_status":  "Ready",
                      "exists":  true,
                      "drift":  false,
                      "enforce_action":  "none",
                      "enforce_ok":  null,
                      "owner":  "waiting_queue",
                      "criticality":  "high",
                      "next_run_time":  "2026-04-07 오전 9:15:00",
                      "last_result":  "0",
                      "execution_healthy":  true
                  },
                  {
                      "task_name":  "\\Bitcoin-WaitingQueue-DualMarket-Daily-Strict",
                      "expected_status":  "Ready",
                      "actual_status":  "Ready",
                      "exists":  true,
                      "drift":  false,
                      "enforce_action":  "none",
                      "enforce_ok":  null,
                      "owner":  "waiting_queue",
                      "criticality":  "high",
                      "next_run_time":  "2026-04-07 오전 9:10:00",
                      "last_result":  "0",
                      "execution_healthy":  true
                  },
                  {
                      "task_name":  "\\Bitcoin-Fused-QuantPixel-SOP-Daily",
                      "expected_status":  "Disabled",
                      "actual_status":  "Disabled",
                      "exists":  true,
                      "drift":  false,
                      "enforce_action":  "none",
                      "enforce_ok":  null,
                      "owner":  "runtime",
                      "criticality":  "medium",
                      "next_run_time":  "N/A",
                      "last_result":  "267011",
                      "execution_healthy":  true
                  },
                  {
                      "task_name":  "\\Bitcoin-KPI-Snapshot-30min",
                      "expected_status":  "Disabled",
                      "actual_status":  "Disabled",
                      "exists":  true,
                      "drift":  false,
                      "enforce_action":  "none",
                      "enforce_ok":  null,
                      "owner":  "runtime",
                      "criticality":  "medium",
                      "next_run_time":  "N/A",
                      "last_result":  "0",
                      "execution_healthy":  true
                  },
                  {
                      "task_name":  "\\Bitcoin-NightWatchmanHarness-DailyGuard-User",
                      "expected_status":  "Disabled",
                      "actual_status":  "Disabled",
                      "exists":  true,
                      "drift":  false,
                      "enforce_action":  "none",
                      "enforce_ok":  null,
                      "owner":  "night_watchman",
                      "criticality":  "medium",
                      "next_run_time":  "N/A",
                      "last_result":  "0",
                      "execution_healthy":  true
                  }
              ]
}

ops_phase1_chain_report_latest.json:
{
    "schema":  "ops_phase1_chain_report_v1",
    "ts_utc":  "2026-04-06T12:18:58.9137222+00:00",
    "runner":  "projects/bitcoin-trading/ops/windows-rehearsal/run_ops_phase1_chain.ps1",
    "scope_note":  "Operational runbook snapshots and gates only; not constitutional interpretation or autonomous strategy changes.",
    "snapshot_exit_code":  0,
    "shared_vault_reachability":  "warning",
    "shared_vault_probe":  {
                               "g_drive_root":  true,
                               "g_vault_probe":  false,
                               "g_vault_path":  "G:\\怨듭쑀 ?쒕씪?대툕\\MKM_DATA_VAULT\\vault"
                           },
    "shared_vault_policy_note":  "G: optional for core ops; see ops_environment_snapshot_latest.json. Warning does not stop chain.",
    "fusion_check_skipped":  false,
    "fusion_exit_code":  0,
    "fusion_ok":  true,
    "include_verify_all_green":  false,
    "verify_all_green_exit_code":  null,
    "verify_all_green_ok":  null,
    "strict_mode":  true,
    "outcome":  "success",
    "overall_chain_ok":  true,
    "artifacts":  {
                      "environment_snapshot":  "C:\\workspace\\projects\\bitcoin-trading\\memory\\v2\\ops\\ops_environment_snapshot_latest.json",
                      "ops_fusion_cycle_status":  "C:\\workspace\\docs\\final\\artifacts\\ops_fusion_cycle_status_latest.json",
                      "all_green_latest":  "C:\\workspace\\projects\\bitcoin-trading\\memory\\v2\\ops\\all_green_latest.json",
                      "phase1_chain_report":  "C:\\workspace\\projects\\bitcoin-trading\\memory\\v2\\ops\\ops_phase1_chain_report_latest.json"
                  }
}

waiting_queue_btc_binance_daily_task.log (tail):
[2026-04-06 02:05:02] INFO close_return source=local_input_json value=-1.1
[2026-04-06 02:05:09] ERROR exception: C:\Python311\python.exe: can't open file 'C:\\workspace\\scripts\\generate_vllm_ab_dataset_expanded.py': [Errno 2] No such file or directory
[2026-04-06 03:05:09] INFO close_return source=local_input_json value=-1.1
[2026-04-06 03:05:16] ERROR exception: C:\Python311\python.exe: can't open file 'C:\\workspace\\scripts\\generate_vllm_ab_dataset_expanded.py': [Errno 2] No such file or directory
[2026-04-06 04:05:02] INFO close_return source=local_input_json value=-1.1
[2026-04-06 04:05:11] ERROR exception: C:\Python311\python.exe: can't open file 'C:\\workspace\\scripts\\generate_vllm_ab_dataset_expanded.py': [Errno 2] No such file or directory
[2026-04-06 05:05:02] INFO close_return source=local_input_json value=-1.1
[2026-04-06 05:05:10] ERROR exception: C:\Python311\python.exe: can't open file 'C:\\workspace\\scripts\\generate_vllm_ab_dataset_expanded.py': [Errno 2] No such file or directory
[2026-04-06 06:05:02] INFO close_return source=local_input_json value=-1.1
[2026-04-06 06:05:10] ERROR exception: C:\Python311\python.exe: can't open file 'C:\\workspace\\scripts\\generate_vllm_ab_dataset_expanded.py': [Errno 2] No such file or directory
[2026-04-06 07:05:02] INFO close_return source=local_input_json value=-1.1
[2026-04-06 07:05:09] ERROR exception: C:\Python311\python.exe: can't open file 'C:\\workspace\\scripts\\generate_vllm_ab_dataset_expanded.py': [Errno 2] No such file or directory
[2026-04-06 08:05:02] INFO close_return source=local_input_json value=-1.1
[2026-04-06 08:05:10] ERROR exception: C:\Python311\python.exe: can't open file 'C:\\workspace\\scripts\\generate_vllm_ab_dataset_expanded.py': [Errno 2] No such file or directory
[2026-04-06 09:05:02] INFO close_return source=local_input_json value=-1.1
[2026-04-06 09:05:09] ERROR exception: C:\Python311\python.exe: can't open file 'C:\\workspace\\scripts\\generate_vllm_ab_dataset_expanded.py': [Errno 2] No such file or directory
[2026-04-06 09:15:02] INFO close_return source=local_input_json value=-1.1
[2026-04-06 09:15:09] ERROR exception: C:\Python311\python.exe: can't open file 'C:\\workspace\\scripts\\generate_vllm_ab_dataset_expanded.py': [Errno 2] No such file or directory
[2026-04-06 09:36:08] INFO close_return source=local_input_json value=-1.1
[2026-04-06 09:36:15] ERROR exception: C:\Python311\python.exe: can't open file 'C:\\workspace\\scripts\\generate_vllm_ab_dataset_expanded.py': [Errno 2] No such file or directory
[2026-04-06 10:05:02] INFO close_return source=local_input_json value=-1.1
[2026-04-06 10:05:09] ERROR exception: C:\Python311\python.exe: can't open file 'C:\\workspace\\scripts\\generate_vllm_ab_dataset_expanded.py': [Errno 2] No such file or directory
[2026-04-06 11:05:02] INFO close_return source=local_input_json value=-1.1
[2026-04-06 11:05:10] ERROR exception: C:\Python311\python.exe: can't open file 'C:\\workspace\\scripts\\generate_vllm_ab_dataset_expanded.py': [Errno 2] No such file or directory
[2026-04-06 12:05:03] INFO close_return source=local_input_json value=-1.1
[2026-04-06 12:05:10] ERROR exception: C:\Python311\python.exe: can't open file 'C:\\workspace\\scripts\\generate_vllm_ab_dataset_expanded.py': [Errno 2] No such file or directory
[2026-04-06 13:05:02] INFO close_return source=local_input_json value=-1.1
[2026-04-06 13:05:09] ERROR exception: C:\Python311\python.exe: can't open file 'C:\\workspace\\scripts\\generate_vllm_ab_dataset_expanded.py': [Errno 2] No such file or directory
[2026-04-06 14:05:03] INFO close_return source=local_input_json value=-1.1
[2026-04-06 14:05:11] ERROR exception: C:\Python311\python.exe: can't open file 'C:\\workspace\\scripts\\generate_vllm_ab_dataset_expanded.py': [Errno 2] No such file or directory
[2026-04-06 15:05:03] INFO close_return source=local_input_json value=-1.1
[2026-04-06 15:05:10] ERROR exception: C:\Python311\python.exe: can't open file 'C:\\workspace\\scripts\\generate_vllm_ab_dataset_expanded.py': [Errno 2] No such file or directory
[2026-04-06 16:05:03] INFO close_return source=local_input_json value=-1.1
[2026-04-06 16:05:11] ERROR exception: C:\Python311\python.exe: can't open file 'C:\\workspace\\scripts\\generate_vllm_ab_dataset_expanded.py': [Errno 2] No such file or directory
[2026-04-06 17:05:02] INFO close_return source=local_input_json value=-1.1
[2026-04-06 17:05:09] ERROR exception: C:\Python311\python.exe: can't open file 'C:\\workspace\\scripts\\generate_vllm_ab_dataset_expanded.py': [Errno 2] No such file or directory
[2026-04-06 18:05:03] INFO close_return source=local_input_json value=-1.1
[2026-04-06 18:05:10] ERROR exception: C:\Python311\python.exe: can't open file 'C:\\workspace\\scripts\\generate_vllm_ab_dataset_expanded.py': [Errno 2] No such file or directory
[2026-04-06 19:05:03] INFO close_return source=local_input_json value=-1.1
[2026-04-06 19:05:11] ERROR exception: C:\Python311\python.exe: can't open file 'C:\\workspace\\scripts\\generate_vllm_ab_dataset_expanded.py': [Errno 2] No such file or directory
[2026-04-06 19:30:24] INFO close_return source=local_input_json value=-1.1
[2026-04-06 19:30:24] INFO close_return source=local_input_json value=-1.1
[2026-04-06 19:30:24] ERROR exception: 'C:\workspace\docs\final\artifacts\waiting_queue_btc_binance_daily_task.stdout.log' 파일은 다른 프로세스에서 사용 중이므로 프로세스에서 액세스할 수 없습니다.
[2026-04-06 19:30:32] ERROR exception: C:\Python311\python.exe: can't open file 'C:\\workspace\\scripts\\generate_vllm_ab_dataset_expanded.py': [Errno 2] No such file or directory
[2026-04-06 19:31:30] INFO close_return source=local_input_json value=-1.1
[2026-04-06 19:31:38] ERROR exception: C:\Python311\python.exe: can't open file 'C:\\workspace\\scripts\\generate_vllm_ab_dataset_expanded.py': [Errno 2] No such file or directory
[2026-04-06 19:33:50] INFO close_return source=local_input_json value=-1.1
[2026-04-06 19:33:59] OK btc binance daily waiting queue success (attempt=1)
[2026-04-06 19:34:54] INFO close_return source=local_input_json value=-1.1
[2026-04-06 19:35:04] OK btc binance daily waiting queue success (attempt=1)
[2026-04-06 19:36:11] INFO close_return source=local_input_json value=-1.1
[2026-04-06 19:36:20] OK btc binance daily waiting queue success (attempt=1)
[2026-04-06 19:38:46] INFO close_return source=local_input_json value=-1.1
[2026-04-06 19:38:54] OK btc binance daily waiting queue success (attempt=1)
[2026-04-06 19:40:01] INFO close_return source=local_input_json value=-1.1
[2026-04-06 19:40:01] INFO close_return source=local_input_json value=-1.1
[2026-04-06 19:40:01] ERROR exception: 'C:\workspace\docs\final\artifacts\waiting_queue_btc_binance_daily_task.stdout.log' 파일은 다른 프로세스에서 사용 중이므로 프로세스에서 액세스할 수 없습니다.
[2026-04-06 19:40:09] ERROR exception: C:\Python311\python.exe: can't open file 'C:\\workspace\\scripts\\generate_vllm_ab_dataset_expanded.py': [Errno 2] No such file or directory
[2026-04-06 19:41:07] INFO close_return source=local_input_json value=-1.1
[2026-04-06 19:41:16] ERROR exception: C:\Python311\python.exe: can't open file 'C:\\workspace\\scripts\\generate_vllm_ab_dataset_expanded.py': [Errno 2] No such file or directory
[2026-04-06 19:41:31] INFO close_return source=local_input_json value=-1.1
[2026-04-06 19:41:40] OK btc binance daily waiting queue success (attempt=1)
[2026-04-06 19:42:39] INFO close_return source=local_input_json value=-1.1
[2026-04-06 19:42:49] OK btc binance daily waiting queue success (attempt=1)
[2026-04-06 19:48:15] INFO close_return source=local_input_json value=-1.1
[2026-04-06 19:48:23] OK btc binance daily waiting queue success (attempt=1)
[2026-04-06 19:50:53] INFO close_return source=local_input_json value=-1.1
[2026-04-06 19:51:02] OK btc binance daily waiting queue success (attempt=1)
[2026-04-06 19:52:09] INFO close_return source=local_input_json value=-1.1
[2026-04-06 19:52:18] OK btc binance daily waiting queue success (attempt=1)
[2026-04-06 19:55:14] INFO close_return source=local_input_json value=-1.1
[2026-04-06 19:55:25] OK btc binance daily waiting queue success (attempt=1)
[2026-04-06 20:05:03] INFO close_return source=local_input_json value=-1.1
[2026-04-06 20:05:11] OK btc binance daily waiting queue success (attempt=1)
[2026-04-06 20:06:18] INFO close_return source=local_input_json value=-1.1
[2026-04-06 20:06:29] OK btc binance daily waiting queue success (attempt=1)
[2026-04-06 21:05:03] INFO close_return source=local_input_json value=-1.1
[2026-04-06 21:05:12] OK btc binance daily waiting queue success (attempt=1)
[2026-04-06 21:06:20] INFO close_return source=local_input_json value=-1.1
[2026-04-06 21:06:29] OK btc binance daily waiting queue success (attempt=1)

waiting_queue_dual_market_daily_task.log (tail):
[2026-04-01 15:16:10] ERROR exit_code=1; stderr_tail=B-Track one-shot runner failed with exit code 1 | At C:\workspace\scripts\run_btrack_gate_and_lock.ps1:26 char:5 | +     throw "B-Track one-shot runner failed with exit code $LASTEXITCOD ... | +     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ |     + CategoryInfo          : OperationStopped: (B-Track one-sho...ith exit code 1:String) [], RuntimeException |     + FullyQualifiedErrorId : B-Track one-shot runner failed with exit code 1 |  
[2026-04-01 15:16:10] ERROR exception: Dual market waiting queue failed with exit code: 1
[2026-04-01 15:16:51] WARN attempt=1/2 exit_code=1; stderr_tail=B-Track one-shot runner failed with exit code 1 | At C:\workspace\scripts\run_btrack_gate_and_lock.ps1:26 char:5 | +     throw "B-Track one-shot runner failed with exit code $LASTEXITCOD ... | +     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ |     + CategoryInfo          : OperationStopped: (B-Track one-sho...ith exit code 1:String) [], RuntimeException |     + FullyQualifiedErrorId : B-Track one-shot runner failed with exit code 1 |  
[2026-04-01 15:17:09] WARN attempt=2/2 exit_code=1; stderr_tail=B-Track one-shot runner failed with exit code 1 | At C:\workspace\scripts\run_btrack_gate_and_lock.ps1:26 char:5 | +     throw "B-Track one-shot runner failed with exit code $LASTEXITCOD ... | +     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ |     + CategoryInfo          : OperationStopped: (B-Track one-sho...ith exit code 1:String) [], RuntimeException |     + FullyQualifiedErrorId : B-Track one-shot runner failed with exit code 1 |  
[2026-04-01 15:17:09] ERROR exception: Dual market waiting queue failed after 2 attempts (last exit code: 1)
[2026-04-01 15:18:05] ERROR exception: Cannot process argument transformation on parameter 'OverlapDriftAlertThreshold'. Cannot convert value "-SkipBundle" to type "System.Double". Error: "Input string was not in a correct format."
[2026-04-01 15:18:49] ERROR exception: B-Track one-shot runner failed with exit code 1
[2026-04-01 15:19:08] ERROR exception: B-Track one-shot runner failed with exit code 1
[2026-04-01 15:20:21] OK dual market waiting queue success (attempt=1)
[2026-04-01 21:54:38] WARN secondary_close_return source=none fallback=PENDING_CLOSE
[2026-04-01 21:54:48] OK dual market waiting queue success (attempt=1)
[2026-04-01 21:55:58] WARN secondary_close_return source=none fallback=PENDING_CLOSE
[2026-04-01 21:56:09] OK dual market waiting queue success (attempt=1)
[2026-04-01 21:57:45] WARN secondary_close_return source=none fallback=PENDING_CLOSE
[2026-04-01 21:57:56] OK dual market waiting queue success (attempt=1)
[2026-04-01 22:02:22] ERROR strict_close_return=true and DAILY_KOSPI_D1_RETURN_PCT is missing
[2026-04-01 22:02:22] ERROR exception: StrictCloseReturn enabled: DAILY_KOSPI_D1_RETURN_PCT must be provided
[2026-04-01 22:14:49] ERROR strict_close_return=true and primary close_return unavailable
[2026-04-01 22:14:49] ERROR exception: StrictCloseReturn enabled: KOSPI close return unavailable from env/yahoo/stooq
[2026-04-01 22:49:53] INFO close_return source=local_input_json value=-0.5
[2026-04-01 22:49:53] INFO secondary_close_return source=local_input_json value=-1.1
[2026-04-01 22:50:00] ERROR exception: C:\Python311\python.exe: can't open file 'C:\\workspace\\scripts\\emit_billing_invoice_from_env.py': [Errno 2] No such file or directory
[2026-04-01 22:50:56] INFO close_return source=local_input_json value=-0.5
[2026-04-01 22:50:56] INFO secondary_close_return source=local_input_json value=-1.1
[2026-04-01 22:51:05] ERROR exception: C:\Python311\python.exe: can't open file 'C:\\workspace\\scripts\\report_billing_evidence_from_vllm.py': [Errno 2] No such file or directory
[2026-04-01 22:52:16] INFO close_return source=local_input_json value=-0.5
[2026-04-01 22:52:16] INFO secondary_close_return source=local_input_json value=-1.1
[2026-04-01 22:52:24] ERROR exception: C:\Python311\python.exe: can't open file 'C:\\workspace\\scripts\\report_fused_paper_cycle_calibration_30.py': [Errno 2] No such file or directory
[2026-04-01 22:52:34] INFO close_return source=local_input_json value=-0.5
[2026-04-01 22:52:34] INFO secondary_close_return source=local_input_json value=-1.1
[2026-04-01 22:52:42] ERROR exception: C:\Python311\python.exe: can't open file 'C:\\workspace\\scripts\\report_fused_paper_cycle_calibration_30.py': [Errno 2] No such file or directory
[2026-04-01 22:53:47] INFO close_return source=local_input_json value=-0.5
[2026-04-01 22:53:47] INFO secondary_close_return source=local_input_json value=-1.1
[2026-04-01 22:53:57] OK dual market waiting queue success (attempt=1)
[2026-04-01 23:00:32] INFO close_return source=local_input_json value=-0.5
[2026-04-01 23:00:32] INFO secondary_close_return source=local_input_json value=-1.1
[2026-04-01 23:00:43] OK dual market waiting queue success (attempt=1)
[2026-04-02 09:10:02] INFO close_return source=local_input_json value=-0.5
[2026-04-02 09:10:02] INFO secondary_close_return source=local_input_json value=-1.1
[2026-04-02 09:10:10] OK dual market waiting queue success (attempt=1)
[2026-04-03 09:10:07] INFO close_return source=local_input_json value=-0.5
[2026-04-03 09:10:07] INFO secondary_close_return source=local_input_json value=-1.1
[2026-04-03 09:10:17] OK dual market waiting queue success (attempt=1)
[2026-04-04 09:10:03] INFO close_return source=local_input_json value=-0.5
[2026-04-04 09:10:03] INFO secondary_close_return source=local_input_json value=-1.1
[2026-04-04 09:10:09] ERROR exception: C:\Python311\python.exe: can't open file 'C:\\workspace\\scripts\\generate_vllm_ab_dataset_expanded.py': [Errno 2] No such file or directory
[2026-04-05 09:10:03] INFO close_return source=local_input_json value=-0.5
[2026-04-05 09:10:03] INFO secondary_close_return source=local_input_json value=-1.1
[2026-04-05 09:10:11] ERROR exception: C:\Python311\python.exe: can't open file 'C:\\workspace\\scripts\\generate_vllm_ab_dataset_expanded.py': [Errno 2] No such file or directory
[2026-04-06 09:10:02] INFO close_return source=local_input_json value=-0.5
[2026-04-06 09:10:02] INFO secondary_close_return source=local_input_json value=-1.1
[2026-04-06 09:10:09] ERROR exception: C:\Python311\python.exe: can't open file 'C:\\workspace\\scripts\\generate_vllm_ab_dataset_expanded.py': [Errno 2] No such file or directory
[2026-04-06 19:30:24] INFO close_return source=local_input_json value=-0.5
[2026-04-06 19:30:24] INFO secondary_close_return source=local_input_json value=-1.1
[2026-04-06 19:30:33] ERROR exception: C:\Python311\python.exe: can't open file 'C:\\workspace\\scripts\\generate_vllm_ab_dataset_expanded.py': [Errno 2] No such file or directory
[2026-04-06 19:34:54] INFO close_return source=local_input_json value=-0.5
[2026-04-06 19:34:54] INFO secondary_close_return source=local_input_json value=-1.1
[2026-04-06 19:35:04] OK dual market waiting queue success (attempt=1)
[2026-04-06 19:40:01] INFO close_return source=local_input_json value=-0.5
[2026-04-06 19:40:01] INFO secondary_close_return source=local_input_json value=-1.1
[2026-04-06 19:40:09] ERROR exception: C:\Python311\python.exe: can't open file 'C:\\workspace\\scripts\\generate_vllm_ab_dataset_expanded.py': [Errno 2] No such file or directory
[2026-04-06 19:49:33] INFO close_return source=local_input_json value=-0.5
[2026-04-06 19:49:33] INFO secondary_close_return source=local_input_json value=-1.1
[2026-04-06 19:49:42] OK dual market waiting queue success (attempt=1)
