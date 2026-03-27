# Constitution/DSS Sequential TODO (2026-03-27)

## Execution Model

- Rule: execute tasks in strict order.
- Parallelism policy: only independent prep/check jobs run in parallel; core execution remains sequential.

## Ordered Tasks

1. [x] Restoration gate re-check
   - `python scripts/run_restoration_regression_20260327.py`
   - success condition: restoration rate 100.0%

2. [x] DSS priority cycle (single action)
   - `python scripts/run_dss_insight_priority_cycle.py --max-actions 1`
   - success condition: `dss_priority_cycle=OK`

3. [x] Unified frontline cycle consolidation
   - `python projects/dss-4d-ingest/run_unified_frontline_cycle.py --tag command_center_followup_20260327_e --auto-base-tag`
   - success condition: `overall_status=PASS`

4. [x] Status refresh and GO verification
   - `python projects/dss-4d-ingest/summarize_latest_frontline_status.py`
   - `python scripts/show_command_center_status.py --compact`
   - success condition: `command_center_status=GO`

5. [x] Update operation notes (this document + progress report)
   - output artifacts updated

6. [x] Scheduler verification for recurring sequential loop
   - check registration and health:
     - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/register_dss_insight_priority_task.ps1 -DryRun`
     - `python scripts/summarize_constitution_scheduler_health.py`
   - success condition: recurring loop task exists and health not degraded

## Latest Fact Snapshot

- command_center_status: `GO`
- local: `DONE/GO`
- remote: `READY:workflow_dispatch_available`
- dss: `PASS/PASS`
- latest unified cycle tag: `command_center_followup_20260327_m_ext3`
