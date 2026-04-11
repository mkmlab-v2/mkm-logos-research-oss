#!/usr/bin/env python3
"""Run the selected ultra compression profile as operational default."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.report_multilens_performance_eval import evaluate_report


INPUT_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
BASELINE_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"
DECISION = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"
ACTIVE_REPORT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
ACTIVE_REPORT_LITERAL = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_LITERAL_V1.json"
ACTIVE_REPORT_ULTRA_LITERAL = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_ULTRA_LITERAL_V1.json"

# Track B (literal-priority): conservative caps — see docs/final/COMPRESSION_SLA_POLICY_V1.md
LITERAL_STRATEGY = "C"
LITERAL_INTENSITY = "high"
LITERAL_GENERAL_MAX_SAVING = 0.28
LITERAL_SENSITIVE_MAX_SAVING = 0.26
LITERAL_HANGUL_MAX_SAVING = 0.30

# Track B — Ultra-Literal (research): maximize Jaccard toward 1.0; accept very low saving — same strategy C.
# Bench proxy: cmp2_001–010 = EN policy/ops (finance-adjacent); cmp2_011–040 = Korean medical/sasang lines.
ULTRA_LITERAL_STRATEGY = "C"
ULTRA_LITERAL_INTENSITY = "high"
ULTRA_LITERAL_GENERAL_MAX_SAVING = 0.06
ULTRA_LITERAL_SENSITIVE_MAX_SAVING = 0.06
ULTRA_LITERAL_HANGUL_MAX_SAVING = 0.08

_FINANCE_OPS_PROXY_IDS = frozenset(f"cmp2_{i:03d}" for i in range(1, 11))
_MEDICAL_KO_PROXY_IDS = frozenset(f"cmp2_{i:03d}" for i in range(11, 41))


def _precision_subset_metrics(cases: list[dict]) -> dict[str, object]:
    """Aggregate Jaccard/saving by bench proxy domain (MULTILENS V2 id bands)."""

    def _agg(id_set: frozenset, label: str) -> dict[str, object] | None:
        rows = [c for c in cases if str(c.get("id", "")) in id_set]
        if not rows:
            return None
        n = len(rows)
        jac = sum(float(r.get("reconstruction_fidelity_jaccard") or 0.0) for r in rows) / n
        sav = sum(float(r.get("token_saving_rate") or 0.0) for r in rows) / n
        o200k = [float(r["o200k_saving_rate"]) for r in rows if r.get("o200k_saving_rate") is not None]
        return {
            "label": label,
            "case_count": n,
            "avg_reconstruction_fidelity_jaccard": jac,
            "avg_token_saving_rate": sav,
            "avg_o200k_saving_rate": (sum(o200k) / len(o200k)) if o200k else None,
        }

    out: dict[str, object] = {
        "schema": "compression_precision_domain_subsets_v1",
        "note": "Proxy bands on MULTILENS_PERFORMANCE_EVAL_INPUT_V2: finance_ops_en=cmp2_001–010; medical_ko=cmp2_011–040.",
    }
    fo = _agg(_FINANCE_OPS_PROXY_IDS, "finance_ops_en_proxy")
    mk = _agg(_MEDICAL_KO_PROXY_IDS, "medical_ko_proxy")
    if fo:
        out["finance_ops_en_proxy"] = fo
    if mk:
        out["medical_ko_proxy"] = mk
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Run ultra compression default profile (Track A universal or Track B literal).")
    ap.add_argument(
        "--mode",
        choices=("universal", "literal", "ultra-literal"),
        default="universal",
        help=(
            "universal: decision-driven ops profile (default). "
            "literal: conservative caps for higher fidelity. "
            "ultra-literal: research profile — very low saving caps, Jaccard toward 1.0 (see COMPRESSION_SLA_POLICY_V1)."
        ),
    )
    ap.add_argument(
        "--apply-gematria-4d-bridge-policy",
        action="store_true",
        help=(
            "Pass apply_gematria_4d_bridge_policy=True into evaluate_report (requires include_gematria_4d_bridge; "
            "adds must_keep terms, may tighten caps, runs _bridge_aware_candidate_select). "
            "Default OFF to match historical active reports."
        ),
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional output path for the report JSON (default: Track A/B active report paths by --mode).",
    )
    args = ap.parse_args()
    sla_track = str(args.mode)

    src_doc = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    baseline_doc = json.loads(BASELINE_V2.read_text(encoding="utf-8"))
    decision_doc = json.loads(DECISION.read_text(encoding="utf-8"))

    selected = decision_doc.get("selected_candidate") or {}
    if sla_track == "literal":
        strategy = LITERAL_STRATEGY
        intensity = LITERAL_INTENSITY
        general_max_saving_rate = LITERAL_GENERAL_MAX_SAVING
        sensitive_max_saving_rate = LITERAL_SENSITIVE_MAX_SAVING
        hangul_max_saving_rate = LITERAL_HANGUL_MAX_SAVING
    elif sla_track == "ultra-literal":
        strategy = ULTRA_LITERAL_STRATEGY
        intensity = ULTRA_LITERAL_INTENSITY
        general_max_saving_rate = ULTRA_LITERAL_GENERAL_MAX_SAVING
        sensitive_max_saving_rate = ULTRA_LITERAL_SENSITIVE_MAX_SAVING
        hangul_max_saving_rate = ULTRA_LITERAL_HANGUL_MAX_SAVING
    else:
        strategy = str(selected.get("strategy", "B"))
        intensity = str(selected.get("intensity", "extreme"))
        general_max_saving_rate = selected.get("general_max_saving_rate")
        sensitive_max_saving_rate = selected.get("sensitive_max_saving_rate")
        hangul_max_saving_rate = selected.get("hangul_max_saving_rate")
        if general_max_saving_rate is not None:
            general_max_saving_rate = float(general_max_saving_rate)
        if sensitive_max_saving_rate is not None:
            sensitive_max_saving_rate = float(sensitive_max_saving_rate)
        if hangul_max_saving_rate is not None:
            hangul_max_saving_rate = float(hangul_max_saving_rate)
    baseline_avg_jaccard = float(
        baseline_doc.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0.0)
    )
    threshold_pp = float(decision_doc.get("target", {}).get("jaccard_drop_threshold_pp", 2.0))

    report = evaluate_report(
        src_doc,
        source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        mode="experimental",
        strategy=strategy,
        intensity=intensity,
        must_keep={"사상의학", "체질", "sasang", "myeongri", "bible"},
        jaccard_drop_threshold_pp=threshold_pp,
        baseline_avg_jaccard=baseline_avg_jaccard,
        general_max_saving_rate=general_max_saving_rate,
        sensitive_max_saving_rate=sensitive_max_saving_rate,
        hangul_max_saving_rate=hangul_max_saving_rate,
        use_domain_router=True,
        use_master_codebook_lexicon_v1=True,
        include_gematria_metadata=True,
        include_gematria_4d_bridge=True,
        apply_gematria_4d_bridge_policy=bool(args.apply_gematria_4d_bridge_policy),
        include_cee_core=True,
    )
    report["active_profile"] = {
        "sla_track": sla_track,
        "from_decision": "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json",
        "strategy": strategy,
        "intensity": intensity,
        "general_max_saving_rate": general_max_saving_rate,
        "sensitive_max_saving_rate": sensitive_max_saving_rate,
        "hangul_max_saving_rate": hangul_max_saving_rate,
        "apply_gematria_4d_bridge_policy": bool(args.apply_gematria_4d_bridge_policy),
    }
    if sla_track == "ultra-literal":
        cases = (report.get("compression_metrics") or {}).get("cases") or []
        if cases:
            report["compression_metrics"]["precision_domain_subsets"] = _precision_subset_metrics(cases)
        report["active_profile"]["research_note"] = (
            "Ultra-Literal: minimize token economy to approach lossless reconstruction on the V2 bench; "
            "not a compliance seal for regulated medical/financial advice."
        )
    out_path = args.out
    if out_path is None:
        out_path = (
            ACTIVE_REPORT_ULTRA_LITERAL
            if sla_track == "ultra-literal"
            else (ACTIVE_REPORT_LITERAL if sla_track == "literal" else ACTIVE_REPORT)
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
