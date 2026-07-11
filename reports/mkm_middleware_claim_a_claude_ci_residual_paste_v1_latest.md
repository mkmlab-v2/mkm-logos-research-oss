# Claude paste — Claim-A honesty wave: repo-runnable CI residual

## Scope
Closes your final text-review limit: **"5/5 exit0 is self-report vs repo"**.
Does **not** ask for market GO / Track A / product SLA upgrade.

## What changed (Fact-Lock)
1. Local deterministic smoke (not chat oral):
   ```text
   py scripts/run_mkm_middleware_claim_a_honesty_ci_smoke_v1.py
   ```
   Artifact: `docs/final/artifacts/mkm_middleware_claim_a_honesty_ci_smoke_v1_latest.json`
   Latest local run: **ok=true** · pytest_external_facing exit0 · headline_reuse_guard exit0

2. GitHub Actions workflow (repo-level, not chat):
   `.github/workflows/middleware-claim-a-honesty-smoke.yml`
   Triggers on Claim-A honesty path changes + `workflow_dispatch`.
   Uploads smoke JSON + headline checklist as CI artifacts.

3. Pytest coverage: `tests/test_external_facing_fact_lock_v1.py` (5) + `tests/test_mkm_middleware_claim_a_honesty_ci_smoke_v1.py` (1) → **6 passed local**.

## Still scoped (self-restraint)
- Headline gate = Claim-A/L0 middleware drafts + send_open/submit-pack — **not every unrelated draft**
- Product grade C+~B- / personal tool B — **unchanged request**
- Blind usefulness tension (plain_full 14>id_only 10) — **still lighted, not buried**
- `ready_for_external_send` a-codeai = **false** (separate lane)

## Ask (honesty axis only)
Confirm: the "self-report vs repo" residual is closed **contingent on** workflow existing in repo + smoke artifact path above.
If you require a green GitHub Actions run URL, that is a separate human push/`workflow_dispatch` step — say so explicitly.
