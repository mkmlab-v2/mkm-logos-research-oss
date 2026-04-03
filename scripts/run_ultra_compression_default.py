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

# Track B (literal-priority): conservative caps — see docs/final/COMPRESSION_SLA_POLICY_V1.md
LITERAL_STRATEGY = "C"
LITERAL_INTENSITY = "high"
LITERAL_GENERAL_MAX_SAVING = 0.28
LITERAL_SENSITIVE_MAX_SAVING = 0.26
LITERAL_HANGUL_MAX_SAVING = 0.30


def main() -> int:
    ap = argparse.ArgumentParser(description="Run ultra compression default profile (Track A universal or Track B literal).")
    ap.add_argument(
        "--mode",
        choices=("universal", "literal"),
        default="universal",
        help="universal: decision-driven ops profile (default). literal: conservative caps for higher fidelity.",
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
    }
    out_path = ACTIVE_REPORT_LITERAL if sla_track == "literal" else ACTIVE_REPORT
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
