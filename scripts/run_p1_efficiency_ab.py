#!/usr/bin/env python3
"""Run P1 A/B candidates using DECISION_V1 gates."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.report_multilens_performance_eval import evaluate_report

INPUT_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
BASELINE_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"
DECISION_V1 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"
OUT_EFFICIENCY_V1 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_P1_AB_EFFICIENCY_V1.json"
OUT_INTENSITY_V1 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_P1_AB_INTENSITY_V1.json"
OUT_BALANCED_V1 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_P1_AB_BALANCED_V1.json"

SASANG_TERMS = {
    "사상의학",
    "체질",
    "sasang",
    "태양인",
    "태음인",
    "소양인",
    "소음인",
    "myeongri",
    "bible",
}


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run P1 A/B scenario.")
    p.add_argument("--input", default=str(INPUT_V2), help="Input eval spec path")
    p.add_argument("--baseline", default=str(BASELINE_V2), help="Baseline report path")
    p.add_argument("--decision", default=str(DECISION_V1), help="Decision V1 path")
    p.add_argument(
        "--profile",
        choices=("efficiency_first", "intensity_first"),
        default="efficiency_first",
        help="Ranking profile for best candidate selection",
    )
    p.add_argument("--output", default="", help="Output JSON path (optional)")
    return p


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _candidate_grid(selected: dict[str, Any]) -> list[dict[str, Any]]:
    s = str(selected.get("strategy") or "A")
    i = str(selected.get("intensity") or "extreme")
    h = bool(selected.get("use_hangul_principle", False))
    gc = float(selected.get("general_max_saving_rate", 0.54))
    sc = float(selected.get("sensitive_max_saving_rate", 0.50))
    hc = float(selected.get("hangul_max_saving_rate", 0.48))

    infra = [
        {"strategy": s, "intensity": i, "use_hangul_principle": h},
        {"strategy": s, "intensity": "ultra", "use_hangul_principle": h},
        {"strategy": "B", "intensity": i, "use_hangul_principle": h},
        {"strategy": s, "intensity": i, "use_hangul_principle": True},
    ]
    caps = [
        (gc, sc, hc),
        (max(0.50, gc - 0.02), max(0.46, sc - 0.01), max(0.42, hc - 0.02)),
        (max(0.50, gc - 0.04), max(0.45, sc - 0.02), max(0.40, hc - 0.04)),
    ]

    rows: list[dict[str, Any]] = []
    for inf in infra:
        for c in caps:
            rows.append(
                {
                    "strategy": inf["strategy"],
                    "intensity": inf["intensity"],
                    "use_hangul_principle": inf["use_hangul_principle"],
                    "general_max_saving_rate": c[0],
                    "sensitive_max_saving_rate": c[1],
                    "hangul_max_saving_rate": c[2],
                }
            )
    return rows


def _score_efficiency_first(row: dict[str, Any]) -> tuple[float, float]:
    return (-float(row["jaccard_drop_pp"]), float(row["global_token_saving_rate"]))


def _score_intensity_first(row: dict[str, Any]) -> tuple[float, float]:
    return (float(row["global_token_saving_rate"]), -float(row["jaccard_drop_pp"]))


def main() -> int:
    t0 = perf_counter()
    args = _parser().parse_args()
    input_doc = _load_json(Path(args.input).resolve())
    baseline_doc = _load_json(Path(args.baseline).resolve())
    decision_doc = _load_json(Path(args.decision).resolve())

    selected = decision_doc.get("selected_candidate") or {}
    target = decision_doc.get("target") or {}
    canary = (decision_doc.get("canary_policy") or {}).get("thresholds") or {}

    baseline_avg_jaccard = float(
        baseline_doc.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0.0)
    )
    saving_rate_min = float(canary.get("saving_rate_min", target.get("saving_rate", 0.5)))
    jaccard_drop_pp_max = float(
        canary.get("jaccard_drop_pp_max", target.get("jaccard_drop_threshold_pp", 1.5))
    )
    sensitive_integrity_min = float(canary.get("sensitive_integrity_min", 0.999))

    candidates = _candidate_grid(selected)
    results: list[dict[str, Any]] = []
    for c in candidates:
        rep = evaluate_report(
            input_doc,
            source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
            mode="experimental",
            strategy=str(c["strategy"]),
            intensity=str(c["intensity"]),
            must_keep=SASANG_TERMS,
            jaccard_drop_threshold_pp=jaccard_drop_pp_max,
            baseline_avg_jaccard=baseline_avg_jaccard,
            general_max_saving_rate=float(c["general_max_saving_rate"]),
            sensitive_max_saving_rate=float(c["sensitive_max_saving_rate"]),
            hangul_max_saving_rate=float(c["hangul_max_saving_rate"]),
            use_hangul_principle=bool(c["use_hangul_principle"]),
            use_domain_router=True,
            include_gematria_metadata=True,
            include_gematria_4d_bridge=True,
            include_cee_core=True,
        )
        cm = rep["compression_metrics"]
        qg = rep["quality_gate"]
        row = {
            **c,
            "global_token_saving_rate": cm["global_token_saving_rate"],
            "avg_reconstruction_fidelity_jaccard": cm["avg_reconstruction_fidelity_jaccard"],
            "avg_sensitive_integrity": cm["avg_sensitive_integrity"],
            "jaccard_drop_pp": qg["jaccard_drop_pp"],
        }
        row["gate_ok"] = bool(
            row["global_token_saving_rate"] >= saving_rate_min
            and row["jaccard_drop_pp"] <= jaccard_drop_pp_max
            and row["avg_sensitive_integrity"] >= sensitive_integrity_min
        )
        results.append(row)

    passing = [r for r in results if r["gate_ok"]]
    score_fn = _score_efficiency_first if args.profile == "efficiency_first" else _score_intensity_first
    ranked = sorted(passing or results, key=score_fn, reverse=True)
    best = ranked[0] if ranked else None
    schema = (
        "multilens_p1_ab_efficiency_v1"
        if args.profile == "efficiency_first"
        else "multilens_p1_ab_intensity_v1"
    )
    out_doc = {
        "schema": schema,
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "profile": args.profile,
        "source_refs": {
            "input": "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
            "baseline": "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json",
            "decision": "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json",
        },
        "gate_contract": {
            "saving_rate_min": saving_rate_min,
            "jaccard_drop_pp_max": jaccard_drop_pp_max,
            "sensitive_integrity_min": sensitive_integrity_min,
        },
        "baseline": {
            "avg_reconstruction_fidelity_jaccard": baseline_avg_jaccard,
        },
        "summary": {
            "candidate_count": len(results),
            "passing_count": len(passing),
            "elapsed_ms": round((perf_counter() - t0) * 1000.0, 3),
        },
        "best_candidate": best,
        "candidates": results,
    }
    default_output = OUT_EFFICIENCY_V1 if args.profile == "efficiency_first" else OUT_INTENSITY_V1
    out_path = Path(args.output).resolve() if args.output else default_output
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path}")
    if best:
        print(
            "BEST:",
            best["strategy"],
            best["intensity"],
            f"saving={best['global_token_saving_rate']:.6f}",
            f"drop_pp={best['jaccard_drop_pp']:.6f}",
            f"gate_ok={best['gate_ok']}",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
