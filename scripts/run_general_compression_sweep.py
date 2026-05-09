#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.report_multilens_performance_eval import evaluate_report

DEFAULT_INPUT = ROOT / "docs" / "final" / "artifacts" / "general_compression_eval_input_v1.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "general_compression_sweep_result_v1.json"

# Full-profile cap grids: low general caps (0.20–0.52) let conservative fidelity floors find GO;
# high band retained. Step sizes balance coverage vs evaluate_report call count (~10k combos × 9 st/it).
FULL_GENERAL_CAPS = (
    0.20,
    0.22,
    0.25,
    0.28,
    0.30,
    0.35,
    0.40,
    0.45,
    0.50,
    0.52,
    0.55,
    0.65,
    0.75,
    0.85,
    0.90,
)
FULL_SENSITIVE_CAPS = (
    0.18,
    0.22,
    0.28,
    0.32,
    0.38,
    0.45,
    0.52,
    0.60,
    0.70,
    0.80,
    0.90,
)
FULL_HANGUL_CAPS = (
    0.18,
    0.22,
    0.28,
    0.35,
    0.42,
    0.50,
    0.58,
    0.65,
    0.72,
    0.80,
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _score(saving: float, jaccard: float, integrity: float) -> float:
    return (0.45 * saving) + (0.45 * jaccard) + (0.10 * integrity)


def main() -> int:
    ap = argparse.ArgumentParser(description="Sweep treatment parameters for general compression benchmark.")
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--fidelity-floor", type=float, default=0.60)
    ap.add_argument("--per-case-fidelity-floor", type=float, default=0.50)
    ap.add_argument("--integrity-floor", type=float, default=0.99)
    ap.add_argument("--min-sensitive-integrity-floor", type=float, default=0.999)
    ap.add_argument("--max-sensitive-violations", type=int, default=0)
    ap.add_argument(
        "--profile",
        choices=("full", "quick"),
        default="full",
        help="full: 3 strategies × 3 intensities × full cap grid (slow). "
        "quick: strategy A only + smaller cap grid for limit probing after fidelity alignment.",
    )
    ap.add_argument(
        "--coherent-caps",
        action="store_true",
        help="Only evaluate (gc, sc, hc) with sc<=gc and hc<=sc (hierarchical cap chain). "
        "Default off: matches historical sweeps where sensitive cap may exceed general cap.",
    )
    args = ap.parse_args()

    doc = _load(args.input)
    baseline_report = evaluate_report(
        doc,
        source_input=str(args.input),
        mode="baseline",
        use_domain_router=True,
        use_master_codebook_lexicon_v1=True,
        experimental_decoder_fidelity_for_baseline=True,
    )
    bcmp = baseline_report.get("compression_metrics") or {}
    baseline_saving = float(bcmp.get("global_token_saving_rate", 0.0))

    if args.profile == "quick":
        strategies = ("A",)
        intensities = ("high", "ultra", "extreme")
        general_caps = (0.35, 0.45, 0.55, 0.65)
        sensitive_caps = (0.30, 0.40, 0.50, 0.60, 0.70)
        hangul_caps = (0.30, 0.40, 0.50, 0.60, 0.70)
    else:
        strategies = ("A", "B", "C")
        intensities = ("high", "ultra", "extreme")
        general_caps = FULL_GENERAL_CAPS
        sensitive_caps = FULL_SENSITIVE_CAPS
        hangul_caps = FULL_HANGUL_CAPS

    candidates: list[dict[str, Any]] = []
    for st in strategies:
        for it in intensities:
            for gc in general_caps:
                for sc in sensitive_caps:
                    for hc in hangul_caps:
                        if args.coherent_caps and (sc > gc or hc > sc):
                            continue
                        report = evaluate_report(
                            doc,
                            source_input=str(args.input),
                            mode="experimental",
                            strategy=st,
                            intensity=it,
                            use_domain_router=True,
                            use_master_codebook_lexicon_v1=True,
                            general_max_saving_rate=gc,
                            sensitive_max_saving_rate=sc,
                            hangul_max_saving_rate=hc,
                        )
                        cmp = report.get("compression_metrics") or {}
                        q = report.get("quality_gate") or {}
                        saving = float(cmp.get("global_token_saving_rate", 0.0))
                        fidelity = float(cmp.get("avg_reconstruction_fidelity_jaccard", 0.0))
                        min_fidelity = float(cmp.get("min_reconstruction_fidelity_jaccard", 0.0))
                        integrity = float(cmp.get("avg_sensitive_integrity", 0.0))
                        min_sensitive_integrity = float(cmp.get("min_sensitive_integrity", 0.0))
                        sensitive_violation_count = int(cmp.get("sensitive_violation_count", 0))
                        gate = {
                            "saving_improved_vs_baseline": saving > baseline_saving,
                            "fidelity_floor_ok": fidelity >= args.fidelity_floor,
                            "per_case_fidelity_floor_ok": min_fidelity >= args.per_case_fidelity_floor,
                            "sensitive_integrity_ok": integrity >= args.integrity_floor,
                            "min_sensitive_integrity_ok": min_sensitive_integrity >= args.min_sensitive_integrity_floor,
                            "sensitive_violation_count_ok": sensitive_violation_count <= args.max_sensitive_violations,
                            # Reuse evaluator's strict leak/avg/min guard as a contract check.
                            "evaluator_sensitive_gate_ok": bool(q.get("sensitive_integrity_ok", False)),
                        }
                        failure_reasons = [k for k, ok in gate.items() if not ok]
                        row = {
                            "strategy": st,
                            "intensity": it,
                            "general_max_saving_rate": gc,
                            "sensitive_max_saving_rate": sc,
                            "hangul_max_saving_rate": hc,
                            "global_token_saving_rate": saving,
                            "avg_reconstruction_fidelity_jaccard": fidelity,
                            "min_reconstruction_fidelity_jaccard": min_fidelity,
                            "avg_sensitive_integrity": integrity,
                            "min_sensitive_integrity": min_sensitive_integrity,
                            "sensitive_violation_count": sensitive_violation_count,
                            "score": _score(saving, fidelity, integrity),
                            "gate": gate,
                            "failure_reasons": failure_reasons,
                            "go": all(gate.values()),
                        }
                        candidates.append(row)

    candidates.sort(key=lambda x: x["score"], reverse=True)
    go_candidates = [c for c in candidates if c["go"]]
    best_score_candidate = candidates[0] if candidates else None
    best_go_candidate = go_candidates[0] if go_candidates else None
    best_candidate = best_go_candidate if best_go_candidate is not None else best_score_candidate
    non_go = [c for c in candidates if not c["go"]]
    top10 = go_candidates[:10] + non_go[: max(0, 10 - len(go_candidates))]
    top10 = top10[:10]
    out = {
        "schema": "general_compression_sweep_result_v1",
        "profile": str(args.profile),
        "coherent_caps": bool(args.coherent_caps),
        "source_input": str(args.input.resolve()),
        "baseline": {
            "global_token_saving_rate": baseline_saving,
            "avg_reconstruction_fidelity_jaccard": float(bcmp.get("avg_reconstruction_fidelity_jaccard", 0.0)),
            "avg_sensitive_integrity": float(bcmp.get("avg_sensitive_integrity", 0.0)),
        },
        "thresholds": {
            "fidelity_floor": args.fidelity_floor,
            "per_case_fidelity_floor": args.per_case_fidelity_floor,
            "integrity_floor": args.integrity_floor,
            "min_sensitive_integrity_floor": args.min_sensitive_integrity_floor,
            "max_sensitive_violations": args.max_sensitive_violations,
            "saving_must_improve_vs_baseline": True,
        },
        "candidate_count": len(candidates),
        "go_candidate_count": len(go_candidates),
        "best_candidate": best_candidate,
        "best_score_candidate": best_score_candidate,
        "best_go_candidate": best_go_candidate,
        "decision": "GO" if go_candidates else "NO_GO",
        "top10": top10,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "decision": out["decision"], "out": str(args.out.resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
