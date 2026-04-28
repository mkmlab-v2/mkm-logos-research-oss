# AI Smartfarm Operation Responsibility (1-Page)

## 1) Purpose
- This document defines clear responsibility boundaries for a 200-300 pyeong pilot where field infrastructure is managed by the farm owner and AI software is managed by our team.

## 2) Scope
- Crop: field crop with drip irrigation and fermented microbe solution.
- Pilot size: one irrigation zone (target 200-300 pyeong).
- Control target: pump and valve automation with manual override.

## 3) Responsibility Matrix
- Field power (220V), pump, tank, piping, filter installation and maintenance: Farm owner.
- Fermentation preparation, raw material input, batch hygiene, and line flushing: Farm owner.
- Sensor data ingestion, control logic, alarm policy, UI, and decision log retention: AI team.
- LTE/router/basic network uptime at site: Farm owner (with remote setup support from AI team).
- Cloud/server uptime and software release management: AI team.

## 4) Command Priority (Hard Rule)
- Priority order is fixed: `Emergency stop > On-site manual > Remote manual > Auto mode`.
- Any manual command immediately preempts automation.
- Auto mode resumes only after explicit human acknowledgment in app.

## 5) Mandatory Site Preconditions (Before AI Go-Live)
- 220V agricultural power is connected and stable near control box.
- Pump, valve, relay, and disk filter pass manual dry-run test.
- Tank outlet filtration and pressure check are validated.
- At least one sensor point reports stable values for 72 hours.

## 6) AI Safety Guardrails (Go-Live Minimum)
- Daily max runtime and max irrigation volume hard limits.
- Single-run max runtime and cooldown interval hard limits.
- Auto stop on communication loss beyond threshold.
- Auto stop on actuator no-ack or pressure anomaly.
- Rain-aware gate enabled (forecast + soil condition combined).

## 7) Incident and Liability Boundary
- Equipment failure due to clogged filter, pump defect, power issue, or plumbing leak: Farm owner domain.
- Wrong trigger due to software logic, invalid threshold config, or server decision bug: AI team domain.
- Shared incidents are classified by timestamped logs and command trace.

## 8) Evidence and Audit Data
- Every ON/OFF action must store: timestamp, reason code, key inputs, command path, ack result.
- Retention period: minimum 12 months for pilot evidence and dispute resolution.

## 9) KPI Review Cadence
- Weekly: runtime, alarm count, manual intervention count.
- Biweekly: soil stability and water-use trend.
- 8-12 week review: baseline vs AI-assisted performance summary.

## 10) Sign-Off
- This document becomes active only after both parties sign and date it.
- Version control is mandatory; any rule change requires explicit re-approval.
