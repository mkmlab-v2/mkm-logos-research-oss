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
from tools.myeongni.manseryeok_provenance import multilens_p1_compression_scope

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

# SSOT: reports/sweep_input_v2_full_144.json — gate_ok row #3 (복원 우선, 절약≥0.5).
# Commander adoption 2026-04-04: strategy/intensity still from candidate grid;
# infra flags fixed to match full-corpus sweep winner (not prior router+bridge+codebook defaults).
P1_EVAL_INFRA_SWEEP_V1: dict[str, bool] = {
    "use_domain_router": False,
    "use_master_codebook_lexicon_v1": False,
    "include_gematria_metadata": True,
    "include_gematria_4d_bridge": False,
    "include_cee_core": True,
}


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run P1 A/B scenario.")
    p.add_argument("--input", default=str(INPUT_V2), help="Input eval spec path")
    p.add_argument("--baseline", default=str(BASELINE_V2), help="Baseline report path")
    p.add_argument("--decision", default=str(DECISION_V1), help="Decision V1 path")
    p.add_argument(
        "--profile",
        choices=("efficiency_first", "intensity_first", "balanced"),
        default="balanced",
        help="Ranking profile for best candidate selection",
    )
    p.add_argument(
        "--balanced-w-saving",
        type=float,
        default=0.45,
        help="balanced profile: weight on global_token_saving_rate",
    )
    p.add_argument(
        "--balanced-w-fidelity",
        type=float,
        default=0.45,
        help="balanced profile: weight on avg_reconstruction_fidelity_jaccard",
    )
    p.add_argument(
        "--balanced-w-drop-penalty",
        type=float,
        default=0.10,
        help="balanced profile: weight on normalized jaccard_drop_pp (0..1 vs gate max)",
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


def _attach_balanced_composite(
    rows: list[dict[str, Any]],
    *,
    jaccard_drop_pp_max: float,
    w_saving: float,
    w_fidelity: float,
    w_drop_penalty: float,
) -> None:
    denom = max(float(jaccard_drop_pp_max), 1e-9)
    for r in rows:
        nd = min(float(r["jaccard_drop_pp"]) / denom, 1.0)
        r["balanced_composite"] = round(
            float(w_saving) * float(r["global_token_saving_rate"])
            + float(w_fidelity) * float(r["avg_reconstruction_fidelity_jaccard"])
            - float(w_drop_penalty) * nd,
            9,
        )


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
            use_domain_router=P1_EVAL_INFRA_SWEEP_V1["use_domain_router"],
            use_master_codebook_lexicon_v1=P1_EVAL_INFRA_SWEEP_V1["use_master_codebook_lexicon_v1"],
            include_gematria_metadata=P1_EVAL_INFRA_SWEEP_V1["include_gematria_metadata"],
            include_gematria_4d_bridge=P1_EVAL_INFRA_SWEEP_V1["include_gematria_4d_bridge"],
            include_cee_core=P1_EVAL_INFRA_SWEEP_V1["include_cee_core"],
            require_tiktoken_o200k=True,
        )
        cm = rep["compression_metrics"]
        qg = rep["quality_gate"]
        row = {
            **c,
            "global_token_saving_rate": cm["global_token_saving_rate"],
            "avg_reconstruction_fidelity_jaccard": cm["avg_reconstruction_fidelity_jaccard"],
            "avg_sensitive_integrity": cm["avg_sensitive_integrity"],
            "jaccard_drop_pp": qg["jaccard_drop_pp"],
            "o200k_token_saving_rate": cm.get("o200k_token_saving_rate"),
            "o200k_saving_rate": cm.get("o200k_saving_rate"),
            "o200k_tokens_before": cm.get("o200k_tokens_before"),
            "o200k_tokens_after": cm.get("o200k_tokens_after"),
            "tiktoken_o200k": cm.get("tiktoken_o200k"),
        }
        row["gate_ok"] = bool(
            row["global_token_saving_rate"] >= saving_rate_min
            and row["jaccard_drop_pp"] <= jaccard_drop_pp_max
            and row["avg_sensitive_integrity"] >= sensitive_integrity_min
        )
        results.append(row)

    passing = [r for r in results if r["gate_ok"]]
    if args.profile == "efficiency_first":
        ranked = sorted(passing or results, key=_score_efficiency_first, reverse=True)
    elif args.profile == "intensity_first":
        ranked = sorted(passing or results, key=_score_intensity_first, reverse=True)
    else:
        _attach_balanced_composite(
            results,
            jaccard_drop_pp_max=jaccard_drop_pp_max,
            w_saving=args.balanced_w_saving,
            w_fidelity=args.balanced_w_fidelity,
            w_drop_penalty=args.balanced_w_drop_penalty,
        )
        ranked = sorted(
            passing or results,
            key=lambda r: float(r["balanced_composite"]),
            reverse=True,
        )
    best = ranked[0] if ranked else None
    if args.profile == "efficiency_first":
        schema = "multilens_p1_ab_efficiency_v1"
    elif args.profile == "intensity_first":
        schema = "multilens_p1_ab_intensity_v1"
    else:
        schema = "multilens_p1_ab_balanced_v1"

    def _repo_rel(path: Path) -> str:
        resolved = path.resolve()
        try:
            return resolved.relative_to(ROOT).as_posix()
        except ValueError:
            return resolved.as_posix()

    out_doc = {
        "schema": schema,
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "profile": args.profile,
        "manseryeok_scope": multilens_p1_compression_scope(),
        "source_refs": {
            "input": _repo_rel(Path(args.input)),
            "baseline": _repo_rel(Path(args.baseline)),
            "decision": _repo_rel(Path(args.decision)),
        },
        "gate_contract": {
            "saving_rate_min": saving_rate_min,
            "jaccard_drop_pp_max": jaccard_drop_pp_max,
            "sensitive_integrity_min": sensitive_integrity_min,
        },
        "baseline": {
            "avg_reconstruction_fidelity_jaccard": baseline_avg_jaccard,
        },
        "p1_eval_infra": {
            "ref": "sweep_input_v2_full_144.json_gate_ok_row_3",
            **P1_EVAL_INFRA_SWEEP_V1,
        },
        "summary": {
            "candidate_count": len(results),
            "passing_count": len(passing),
            "elapsed_ms": round((perf_counter() - t0) * 1000.0, 3),
        },
        "best_candidate": best,
        "candidates": results,
    }
    if args.profile == "balanced":
        out_doc["balanced_weights"] = {
            "w_saving": args.balanced_w_saving,
            "w_fidelity": args.balanced_w_fidelity,
            "w_drop_penalty": args.balanced_w_drop_penalty,
            "normalized_drop_divisor": jaccard_drop_pp_max,
            "formula": "w_saving*saving + w_fidelity*avg_jaccard - w_drop_penalty*min(drop_pp/divisor,1)",
        }
    default_output = (
        OUT_EFFICIENCY_V1
        if args.profile == "efficiency_first"
        else (OUT_INTENSITY_V1 if args.profile == "intensity_first" else OUT_BALANCED_V1)
    )
    out_path = Path(args.output).resolve() if args.output else default_output
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path}")
    if best:
        line = [
            "BEST:",
            best["strategy"],
            best["intensity"],
            f"saving={best['global_token_saving_rate']:.6f}",
            f"drop_pp={best['jaccard_drop_pp']:.6f}",
            f"gate_ok={best['gate_ok']}",
        ]
        if args.profile == "balanced" and "balanced_composite" in best:
            line.append(f"composite={best['balanced_composite']:.6f}")
        print(*line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
