# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.9, K:0.5, M:0.2}
# Balance: 92
# Purpose: Run Track A must-keep A/B regression with hard gates.
# Keywords: track_a, must_keep, ab_test, regression, commercialization
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.report_multilens_performance_eval import evaluate_report

INPUT_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
ACTIVE_A = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
RULES = ROOT / "docs" / "final" / "artifacts" / "track_a_failure_pattern_rules_v1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_must_keep_ab_result_v1.json"

BASE_MUST_KEEP = {"사상의학", "체질", "sasang", "myeongri", "bible"}


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _metric_triplet(report: dict[str, Any]) -> tuple[float, float, float]:
    m = report.get("compression_metrics", {})
    return (
        float(m.get("global_token_saving_rate", 0.0)),
        float(m.get("avg_reconstruction_fidelity_jaccard", 0.0)),
        float(m.get("avg_sensitive_integrity", 0.0)),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=INPUT_V2)
    ap.add_argument("--active-a-report", type=Path, default=ACTIVE_A)
    ap.add_argument("--rules", type=Path, default=RULES)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--top-n", type=int, default=20)
    ap.add_argument("--saving-floor", type=float, default=0.49)
    ap.add_argument("--integrity-floor", type=float, default=1.0)
    args = ap.parse_args()

    input_doc = _load_json(args.input if args.input.is_absolute() else ROOT / args.input)
    active_doc = _load_json(args.active_a_report if args.active_a_report.is_absolute() else ROOT / args.active_a_report)
    rules_doc = _load_json(args.rules if args.rules.is_absolute() else ROOT / args.rules)

    active_profile = active_doc.get("active_profile", {})
    strategy = str(active_profile.get("strategy", "A"))
    intensity = str(active_profile.get("intensity", "extreme"))
    gc = active_profile.get("general_max_saving_rate", 0.54)
    sc = active_profile.get("sensitive_max_saving_rate", 0.5)
    hc = active_profile.get("hangul_max_saving_rate", 0.48)
    gc = float(gc) if gc is not None else None
    sc = float(sc) if sc is not None else None
    hc = float(hc) if hc is not None else None

    candidate_tokens = [
        str(row.get("token") or "").strip().lower()
        for row in rules_doc.get("must_keep_candidates", [])
        if str(row.get("token") or "").strip()
    ][: max(1, args.top_n)]
    candidate_tokens = [t for t in candidate_tokens if len(t) >= 2]
    treatment_must_keep = set(BASE_MUST_KEEP) | set(candidate_tokens)

    common = dict(
        source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        mode="experimental",
        strategy=strategy,
        intensity=intensity,
        general_max_saving_rate=gc,
        sensitive_max_saving_rate=sc,
        hangul_max_saving_rate=hc,
        use_domain_router=True,
        use_master_codebook_lexicon_v1=True,
        include_gematria_metadata=True,
        include_gematria_4d_bridge=True,
        include_cee_core=True,
    )

    baseline = evaluate_report(input_doc, must_keep=set(BASE_MUST_KEEP), **common)
    treatment = evaluate_report(input_doc, must_keep=treatment_must_keep, **common)

    b_save, b_jac, b_int = _metric_triplet(baseline)
    t_save, t_jac, t_int = _metric_triplet(treatment)

    delta_save = t_save - b_save
    delta_jac = t_jac - b_jac
    delta_int = t_int - b_int

    gate = {
        "saving_floor_ok": t_save >= args.saving_floor,
        "integrity_floor_ok": t_int >= args.integrity_floor,
        "jaccard_non_regression_ok": delta_jac >= 0.0,
        "jaccard_uplift_2pp_ok": delta_jac >= 0.02,
    }
    decision = (
        "GO_MUST_KEEP_RULESET_V1"
        if gate["saving_floor_ok"] and gate["integrity_floor_ok"] and gate["jaccard_non_regression_ok"]
        else "HOLD_BASELINE_TRACK_A"
    )

    out_doc = {
        "schema": "track_a_must_keep_ab_result_v1",
        "generated_at_utc": _now_utc(),
        "inputs": {
            "input": str(args.input),
            "active_a_report": str(args.active_a_report),
            "rules": str(args.rules),
            "top_n": args.top_n,
            "base_must_keep": sorted(BASE_MUST_KEEP),
            "candidate_tokens": candidate_tokens,
        },
        "metrics": {
            "baseline": {
                "global_token_saving_rate": b_save,
                "avg_reconstruction_fidelity_jaccard": b_jac,
                "avg_sensitive_integrity": b_int,
            },
            "treatment": {
                "global_token_saving_rate": t_save,
                "avg_reconstruction_fidelity_jaccard": t_jac,
                "avg_sensitive_integrity": t_int,
            },
            "delta": {
                "global_token_saving_rate": delta_save,
                "avg_reconstruction_fidelity_jaccard": delta_jac,
                "avg_sensitive_integrity": delta_int,
            },
        },
        "gate": gate,
        "decision": decision,
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(out_path),
                "decision": decision,
                "delta_jaccard": delta_jac,
                "delta_saving": delta_save,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
