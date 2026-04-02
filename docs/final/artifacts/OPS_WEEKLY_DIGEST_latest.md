# OPS Weekly Digest (2026-04-02 15:37 UTC)

## Baseline
- overall_ok: True
- degraded: False
- go_no_go: UNKNOWN
- recommended_stage: UNKNOWN

## Integrity Gates
- strict_task_schedule_ok: True
- ops_task_schedule_ok: True
- compression_stub_health_ok: True
- prophecy_alignment_pytest_ok: True

## Event-Based Trigger Rule
- Trigger immediate report when one of below is true:
  - overall_ok=false
  - degraded=true
  - strict_task_schedule_ok=false
  - ops_task_schedule_ok=false
