# MKM Submission Preflight 10-Minute Checklist (v1)

## 1) Claim Guard Status

- Open `docs/final/artifacts/external_message_claim_guard_latest.json`
- Confirm `summary.status == "pass"`

## 2) Core Evidence 5-Pack Freshness

Verify existence and `generated_at_utc` for:

- `docs/final/artifacts/two_track_raw_oos_readiness_latest.json`
- `docs/final/artifacts/two_track_statistical_significance_report_latest.json`
- `docs/final/artifacts/two_track_benchmark_comparison_latest.json`
- `docs/final/artifacts/two_track_falsification_suite_latest.json`
- `docs/final/artifacts/two_track_falsification_boundary_report_latest.json`

## 3) Abstract/Template Consistency

Ensure wording is aligned across:

- `docs/final/artifacts/mkm_submission_packet_v1.md` (KDD/AAAI final abstracts)
- `docs/final/artifacts/two_track_submission_camera_ready_latest.json`
- `docs/final/artifacts/two_track_kdd_submission_template_latest.json`

## 4) Compliance Phrase Check

### Disallowed wording

- guaranteed return
- directional certainty
- doctrinal proof (as positive claim)

### Required wording

- as-of artifact snapshot
- A-track/B-track separation
- risk-control purpose

## 5) Evidence Tier Label Check

- In manuscript tables, keep P1-P5 as `Tier A candidate` unless promotion is explicitly completed.
- Do not present `research_only` artifacts as production-validated outcomes.

## 6) Boundary and Limitation Section Check

Ensure manuscript includes:

- snapshot dependence statement
- first non-pass boundary disclosure
- no auto-promotion from B-track to A-track

## 7) Submission Packet Integrity

- Confirm file versions and names are synchronized in `docs/final/artifacts/`.
- Ensure latest commit reflects the exact text being submitted.

## 8) Reproducibility One-Liner Ready

Prepare one command + one output path sentence for reviewer response:

- Command: `<repro command>`
- Output: `<artifact path>`

## 9) Ops Task Safety Check (Operational Readiness)

- Confirm scheduled tasks are `Ready`:
  - `A-Track Weekly GoNoGo-Dev`
  - `A-Track Weekly GoNoGo-Prod`
- Confirm Prod task args do **not** include `-SkipClaimGuard`.

## 10) Final Disclosure Lines (Copy/Paste)

- `All values are as-of artifact snapshots under fixed evaluation settings.`
- `Outputs are for risk-control governance, not guaranteed directional return.`

