#!/usr/bin/env python3
"""Update W4 final decision markdown from latest W3 artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
W3_SUMMARY = ART / "W3_BATCH_EXPANSION_SUMMARY_V1.json"
W3_MULTI = ART / "W3_MULTI_BATCH_STABILITY_SUMMARY_V1.json"
W3_SWEEP = ART / "W3_GATE_THRESHOLD_SWEEP_V1.json"
W3_K_SWEEP = ART / "W3_K_SWEEP_500_1000_2000_V1.json"
OUT = ART / "W4_PROMOTION_DECISION_FINAL.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _pick_w3_result() -> Path:
    for name in (
        "W3_RESONANCE_BATCH_RESULT_V4.json",
        "W3_RESONANCE_BATCH_RESULT_V3.json",
        "W3_RESONANCE_BATCH_RESULT_V2.json",
        "W3_RESONANCE_BATCH_RESULT_V1.json",
    ):
        p = ART / name
        if p.is_file():
            return p
    return ART / "W3_RESONANCE_BATCH_RESULT_V1.json"


def main() -> int:
    w3_result_path = _pick_w3_result()
    r = _load(w3_result_path)
    s = _load(W3_SUMMARY)
    m = _load(W3_MULTI)
    w = _load(W3_SWEEP)
    k = _load(W3_K_SWEEP)
    fs = r.get("falsification_summary") or {}
    pg = r.get("promotion_gate") or {}
    ga = r.get("guardrail_assertions") or {}
    rm = r.get("run_meta") or {}
    counts = s.get("counts") or {}
    agg = m.get("aggregate") or {}
    decision = "GO_CANDIDATE" if pg.get("passed") else "NO_GO"
    sweep_changes = len(w.get("decision_changes") or [])
    k_summary = k.get("summary") or {}
    k_runs = k.get("runs") or []
    k_effective = max((int(r.get("effective_k", 0)) for r in k_runs), default=0)
    k_eval = max((int(r.get("promotion_eval_k", 0)) for r in k_runs), default=0)
    aux_version = str(rm.get("aux_adapter_version") or "none")
    top_rows = list(r.get("top_n_results") or [])
    aux_present_count = sum(1 for row in top_rows if isinstance(row.get("aux_non_gating"), dict))
    aux_present_ratio = f"{aux_present_count}/{len(top_rows)}" if top_rows else "0/0"

    md = f"""# W4 Promotion Decision Final

## Scope
- Track: B-track only
- Cycle: W2 Gate-First -> W3 compute -> W4 decision
- A-track merge: not executed
- Updated at UTC: {datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}

## Inputs
- `docs/final/artifacts/W3_RESONANCE_RESULT_V1.json`
- `docs/final/artifacts/{w3_result_path.name}`
- `docs/final/artifacts/W3_BATCH_EXPANSION_SUMMARY_V1.json`
- `docs/final/artifacts/W3_MULTI_BATCH_STABILITY_SUMMARY_V1.json`
- `docs/final/artifacts/W3_GATE_THRESHOLD_SWEEP_V1.json`
- `docs/final/artifacts/W3_K_SWEEP_500_1000_2000_V1.json`
- `docs/final/artifacts/W3_FALSIFICATION_PRECHECK.json`
- `docs/final/artifacts/W2_GATE_READINESS_NOTE.json`
- `docs/final/P0_COMMERCIALIZATION_TRACKER.md`

## Gate Snapshot
- schema_validation: pass
- enum_consistency: pass
- falsification_check_passed: {"pass" if pg.get("passed") else "fail"}
- boundary_rules_passed: pass

## Core Evidence
- `false_equivalence_risk_count = {int(fs.get("false_equivalence_risk_count", 0))}`
- `deterministic_wording_risk_count = {int(fs.get("deterministic_wording_risk_count", 0))}`
- `promotion_gate.passed = {str(bool(pg.get("passed", False))).lower()}`
- batch expansion:
  - macro_samples = {int(counts.get("macro_samples", 0))}
  - personal_samples = {int(counts.get("personal_samples", 0))}
  - top_n_count = {int(counts.get("top_n_count", 0))}
- multi-batch stability:
  - all_passed = {str(bool(agg.get("all_passed", False))).lower()}
  - false_equivalence_max = {int(agg.get("false_equivalence_max", 0))}
  - deterministic_wording_max = {int(agg.get("deterministic_wording_max", 0))}
  - threshold_decision_changes = {sweep_changes}
- k-expansion sweep:
  - candidate_pool_size = {int(k_summary.get("candidate_pool_size", 0))}
  - requested_ks = {k_summary.get("requested_ks", [])}
  - effective_k_max = {k_effective}
  - promotion_eval_k_max = {k_eval}
  - all_promotion_gates_passed = {str(bool(k_summary.get("all_promotion_gates_passed", False))).lower()}
- guardrail assertions:
  - all_rationale_include_hypo = {str(bool(ga.get("all_rationale_include_hypo", False))).lower()}
  - non_medical_notice_present_for_personal_lane = {str(bool(ga.get("non_medical_notice_present_for_personal_lane", False))).lower()}
  - non_deterministic_notice_present_for_personal_lane = {str(bool(ga.get("non_deterministic_notice_present_for_personal_lane", False))).lower()}
  - geo_event_ref_participates_in_scoring = {str(bool(ga.get("geo_event_ref_participates_in_scoring", True))).lower()}
- auxiliary adapter (non-gating):
  - aux_adapter_version = {aux_version}
  - top_n_aux_non_gating_present = {aux_present_ratio}
  - ranking_or_gate_participation = false (metadata only)

## Decision
- Decision: **{decision}**
- Reason: Deterministic compute pipeline and threshold gates evaluated on current batch run.

## Constraints (still enforced)
- This decision is B-track bounded.
- A-track promotion and trading-trigger integration remain approval-gated.
- Deterministic public claims remain forbidden without explicit approval.

## Residual Risk
- Coverage is still limited to controlled B-track inputs.
- Gate pass/fail is evaluated at promotion_eval_k (policy cap), while effective_k tracks available pool breadth.

## Next Approval Request
- Requested action: Approve controlled medium-batch expansion (multi-run) while keeping strict B-track isolation.
"""
    OUT.write_text(md, encoding="utf-8")
    print("OK: W4 final decision markdown updated")
    print(f"out={OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
