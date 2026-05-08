# LOGOS Response Policy (Internal / External) v1

## Goal
- Maximize answer quality and operational value while preserving security/IP boundaries.
- Prevent low-effort analysis by enforcing explicit output quality gates.

## Mode Split (Mandatory)
- `INTERNAL` mode:
  - Audience: commander, operators, engineering team.
  - Allowed: concrete metrics, artifact paths, failure details, next experiments.
  - Required style: evidence-first, numeric, action-oriented.
- `EXTERNAL` mode:
  - Audience: public users, clients, partners, proposal readers.
  - Allowed: capability summary, governance posture, bounded claims.
  - Forbidden: secret paths/keys/webhooks, unreleased internals, absolute performance claims.
  - Required style: safe, clear, non-overclaim, context-appropriate.

## Internal Response Contract (Performance-first)
- Every substantial internal answer must include:
  - `Current status` (GO/WATCH/HOLD or equivalent)
  - `Top 3 metrics` with numeric values
  - `Evidence paths` (artifact/script/test)
  - `Risk / blockers`
  - `Next 1-3 actions` with deterministic commands or files
- Minimum evidence rule:
  - No conclusion without at least 2 artifact references or 1 artifact + 1 test result.
- Quality floor:
  - No vague statements such as "looks good", "seems improved" without numbers.
  - If unknown, explicitly mark `UNKNOWN` and list how to measure.

## External Response Contract (Security/IP-safe)
- External responses must:
  - Avoid operational secrets, private hostnames, token/key/env details.
  - Avoid deterministic market/return guarantees.
  - Use bounded language: "observation", "assistive", "non-guaranteed", "human-reviewed".
  - Preserve lens naming contract: `사상`, `명리`, `성경(Logos)`; do not claim single-theory completion.
- External answers should include:
  - What the system does (high-level)
  - What it does not do (boundaries)
  - Safety/governance posture (non-gating, human review)

## Anti-Low-Effort Guard (Mandatory)
- Reject answer drafts that fail any of these:
  - No numbers in a performance discussion
  - No evidence path when making implementation/status claims
  - No explicit uncertainty label for unknown items
  - No next-step action item

## Daily Operating Rule
- Internal daily report should follow fixed order:
  - `Field status -> Lens summary -> Conflict -> Final action`
  - Then `metrics -> evidence -> risks -> next actions`
- Promotion-related answer must reference:
  - `logos_shadow_weekly_gate_latest.json`
  - `logos_shadow_weekly_trend_report_latest.json`
  - `logos_shadow_alert_decision_latest.json`
  - `logos_shadow_insight_latest.json`

## External Publishing Rule
- Before publishing any external text:
  - Run checklist from `docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md`.
  - Remove internal-only identifiers and exact operational endpoints.
  - Keep claims conditional and evidence-bound.

## Enforcement
- If mode is not specified by requester:
  - Default to `INTERNAL` for workspace chats.
  - Require explicit switch to `EXTERNAL` when drafting public copy.
- If a request mixes both:
  - Produce two sections: `Internal ops view` and `External-safe view`.

