# Global Atom Corpus Profile Change Approval Checklist v1

## Purpose
- Prevent ambiguity when changing `corpus_profile_id` across Global Atom artifacts.
- Enforce reproducibility, auditability, and legal-safe external messaging.

## Approved Profile IDs
- `canon_only_v1`
- `canon_plus_deuterocanon_v1`
- `canon_plus_dss_apocrypha_v1`

## Change Request Fields (Required)
- `requested_profile_id`:
- `current_profile_id`:
- `reason_for_change`:
- `affected_scope`:
  - claim lock
  - anchor
  - atom set
  - onepagers (latest + freeze)
  - public/academic briefs
- `risk_assessment`:
- `requested_by`:
- `requested_at_utc`:

## Pre-Approval Evidence (Must PASS)
- `py scripts/check_global_atom_claim_lock_v1.py --strict`
- `py scripts/check_global_atom_edge_claim_atom_set_v1.py --strict`
- `py scripts/check_global_atom_corpus_profile_lock_v1.py --strict`
- If historical artifacts are impacted:
  - `py scripts/backfill_global_atom_onepager_corpus_profile_v1.py --write`

## Post-Change Validation (Must PASS)
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_global_atom_claim_lock_daily.ps1`
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_p0_constitution_gate_paths.ps1`

## External Messaging Guard (Mandatory)
- First sentence must include:
  - `corpus_profile_id`
  - `anchor_freeze_id`
  - `current_edge_count`
  - `latest_minus_anchor_edge`
- Forbidden statements:
  - universal constant claims across all runs/corpora
  - single-metric commercial performance guarantees

## Approval Record
- `approved_by`:
- `approved_at_utc`:
- `approval_note`:
