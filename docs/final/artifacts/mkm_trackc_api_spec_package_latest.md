# MKM Macro Risk Warning API Spec Package (v1)

- generated_at_utc: `2026-05-03T10:29:12.818163Z`
- endpoint: `GET /v1/macro-risk-warning`

## Request Contract
- required query: `asset_scope`
- optional header: `x-request-id`

## Response Snapshot (Live)
- decision_state: `WATCH`
- risk_warning_level: `elevated`
- confidence_band: `medium`
- posture: `watch_tighten`
- ttl_seconds: `900`

## Policy Binding
- binding_status: `mapped`
- client_action: `tighten_monitoring_and_reduce_leverage`
- new_entry_policy: `restricted`

## Error/Fallback Contract
- `http_503_service_unavailable` -> `UNAVAILABLE` / `use_internal_safe_defaults_and_escalate`
- `timeout_empty_payload` -> `UNAVAILABLE` / `use_internal_safe_defaults_and_escalate`

## SLA and Guardrails
- signal_ttl_seconds: `900`
- advisory_only: `True`
- operator_final_decision: `True`
- Track A/B automatic bridge disabled
