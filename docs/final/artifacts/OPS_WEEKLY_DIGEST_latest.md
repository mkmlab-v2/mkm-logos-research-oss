# OPS Weekly Digest (2026-04-20 01:20 UTC)

## Baseline
- overall_ok: false
- degraded: true
- go_no_go: UNKNOWN
- recommended_stage: UNKNOWN

## Integrity Gates
- strict_task_schedule_ok: n/a
- ops_task_schedule_ok: n/a
- compression_stub_health_ok: n/a
- prophecy_alignment_pytest_ok: n/a

## Event-Based Trigger Rule
- Trigger immediate report when one of below is true:
  - overall_ok=false
  - degraded=true
  - strict_task_schedule_ok=false
  - ops_task_schedule_ok=false
