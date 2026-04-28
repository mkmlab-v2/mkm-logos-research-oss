# B2B PoC 4-Week Execution Checklist v1

## Week 1 — Contract and Gate Lock

- Define target workload lane and exclusions
- Freeze PoC success criteria and thresholds
- Confirm sync policy (daily full + hourly delta)
- Confirm rollback authority and incident channel
- Baseline artifacts captured and archived

## Week 2 — Shadow Deployment

- Deploy runtime config from decision artifact
- Run shadow router only (no production path disruption)
- Enable daily shadow report generation
- Enable health alert and guard pipeline
- Validate evidence paths and report delivery

## Week 3 — Controlled Activation

- Run guarded activation in agreed windows
- Execute forced-alert guard drill and confirm downgrade behavior
- Track:
  - candidate-ok rate
  - unresolved token trend
  - fallback frequency
  - decision distribution
- Record incidents and mitigations

## Week 4 — KPI Review and Conversion Decision

- Compare baseline vs PoC evidence bundle
- Assess cost-efficiency and reliability together
- Finalize:
  - GO production
  - EXTEND PoC
  - HOLD and closeout
- Publish signed closeout note

## Must-Have Evidence Bundle

- `genesis_pointer_routing_control_chain_latest.json`
- `genesis_pointer_routing_decision_guarded_latest.json`
- `genesis_pointer_route_runtime_config_latest.json`
- `pointer_hash_snapping_router_shadow_daily_report_latest.json`
- `pointer_hash_snapping_router_shadow_alert_latest.json`
- `pointer_shadow_guard_drill_latest.json`

## Exit Rules

- Immediate fallback to Track A on alert/guard trigger
- No unconditional performance claim allowed in external reporting
- Conversion only with both technical and business sign-off

