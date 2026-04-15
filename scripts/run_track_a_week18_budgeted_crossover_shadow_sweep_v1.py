# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.3}
# Balance: 93
# Purpose: Run Week-18 E2 budgeted crossover with dynamic floor shadow sweep.
# Keywords: track_a, week18, budgeted_crossover, shadow_floor, sweep
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
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
PACK = ROOT / "docs" / "final" / "artifacts" / "track_a_week18_hypothesis_pack_v1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_week18_budgeted_crossover_shadow_sweep_v1.json"

BASE_MUST_KEEP = {"사상의학", "체질", "sasang", "myeongri", "bible"}


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_e2_config(pack_doc: dict[str, Any]) -> tuple[list[float], list[float], list[float]]:
    experiments = ((pack_doc.get("pack") or {}).get("experiments") or [])
    e2 = next((x for x in experiments if str(x.get("id")) == "W18-E2"), {})
    cfg = e2.get("config") or {}
    crossover_weight_grid = [float(x) for x in (cfg.get("crossover_weight_grid") or [])]
    floor_shadow_margin_grid = [float(x) for x in (cfg.get("floor_shadow_margin_grid") or [])]
    confidence_budget_grid = [float(x) for x in (cfg.get("confidence_budget_grid") or [])]
    return (
        crossover_weight_grid or [0.56, 0.61, 0.66],
        floor_shadow_margin_grid or [0.0, 0.0008, 0.002],
        confidence_budget_grid or [0.1, 0.12, 0.14],
    )


def _build_case_map(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = (report.get("compression_metrics", {}) or {}).get("cases", [])
    return {str((r or {}).get("id")): r for r in rows if str((r or {}).get("id"))}


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _hash_unit(value: str) -> float:
    raw = hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]
    return int(raw, 16) / 0xFFFFFFFF


def _summarize(cases: list[dict[str, Any]]) -> dict[str, float]:
    return {
        "global_token_saving_rate": _avg([float(c.get("token_saving_rate", 0.0)) for c in cases]),
        "avg_reconstruction_fidelity_jaccard": _avg([float(c.get("reconstruction_fidelity_jaccard", 0.0)) for c in cases]),
        "avg_sensitive_integrity": _avg([float(c.get("sensitive_integrity", 0.0)) for c in cases]),
        "sensitive_leak_rate": _avg([1.0 if bool(c.get("sensitive_leak", False)) else 0.0 for c in cases]),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=INPUT_V2)
    ap.add_argument("--active-a-report", type=Path, default=ACTIVE_A)
    ap.add_argument("--pack", type=Path, default=PACK)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--saving-floor", type=float, default=0.49)
    ap.add_argument("--jaccard-floor", type=float, default=0.85)
    ap.add_argument("--integrity-floor", type=float, default=1.0)
    args = ap.parse_args()

    input_doc = _load_json(args.input if args.input.is_absolute() else ROOT / args.input)
    active_doc = _load_json(args.active_a_report if args.active_a_report.is_absolute() else ROOT / args.active_a_report)
    pack_doc = _load_json(args.pack if args.pack.is_absolute() else ROOT / args.pack)
    crossover_weights, floor_margins, confidence_budgets = _read_e2_config(pack_doc)

    active_profile = active_doc.get("active_profile", {})
    strategy = str(active_profile.get("strategy", "A"))
    intensity = str(active_profile.get("intensity", "extreme"))
    gc = float(active_profile.get("general_max_saving_rate", 0.54))
    sc = float(active_profile.get("sensitive_max_saving_rate", 0.5))
    hc = float(active_profile.get("hangul_max_saving_rate", 0.48))

    router_on = evaluate_report(
        input_doc,
        source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        mode="experimental",
        strategy=strategy,
        intensity=intensity,
        must_keep=set(BASE_MUST_KEEP),
        general_max_saving_rate=gc,
        sensitive_max_saving_rate=sc,
        hangul_max_saving_rate=hc,
        use_domain_router=True,
        use_master_codebook_lexicon_v1=True,
        include_gematria_metadata=True,
        include_gematria_4d_bridge=True,
        include_cee_core=True,
    )
    router_off = evaluate_report(
        input_doc,
        source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        mode="experimental",
        strategy=strategy,
        intensity=intensity,
        must_keep=set(BASE_MUST_KEEP),
        general_max_saving_rate=gc,
        sensitive_max_saving_rate=sc,
        hangul_max_saving_rate=hc,
        use_domain_router=False,
        use_master_codebook_lexicon_v1=True,
        include_gematria_metadata=True,
        include_gematria_4d_bridge=True,
        include_cee_core=True,
    )

    on_map = _build_case_map(router_on)
    off_map = _build_case_map(router_off)
    baseline = _summarize(list(on_map.values()))

    runs: list[dict[str, Any]] = []
    for crossover_weight in crossover_weights:
        for floor_margin in floor_margins:
            for confidence_budget in confidence_budgets:
                selected: list[dict[str, Any]] = []
                switched_to_off = 0
                crossover_win_cases = 0
                floor_shadow_blocked = 0
                confidence_blocked = 0
                total = 0
                floor_shadow = args.saving_floor + floor_margin
                for cid, on_case in on_map.items():
                    off_case = off_map.get(cid)
                    if not off_case:
                        selected.append(on_case)
                        total += 1
                        continue

                    on_s = float(on_case.get("token_saving_rate", 0.0))
                    off_s = float(off_case.get("token_saving_rate", 0.0))
                    on_j = float(on_case.get("reconstruction_fidelity_jaccard", 0.0))
                    off_j = float(off_case.get("reconstruction_fidelity_jaccard", 0.0))

                    if off_s < floor_shadow:
                        selected.append(on_case)
                        floor_shadow_blocked += 1
                        total += 1
                        continue

                    confidence = _hash_unit(f"w18-e2:confidence:{cid}:{crossover_weight}:{floor_margin}:{confidence_budget}")
                    if confidence > confidence_budget:
                        selected.append(on_case)
                        confidence_blocked += 1
                        total += 1
                        continue

                    crossover_component = (off_j - on_j) * crossover_weight
                    saving_component = (off_s - on_s) * (1.0 - crossover_weight)
                    noise = (_hash_unit(f"w18-e2:score:{cid}:{crossover_weight}:{floor_margin}:{confidence_budget}") - 0.5) * 0.001
                    score = crossover_component + saving_component + noise
                    threshold = 0.00055 - (0.0013 * confidence_budget)
                    use_off = score > threshold
                    if use_off and (off_j >= on_j):
                        crossover_win_cases += 1
                    selected.append(off_case if use_off else on_case)
                    if use_off:
                        switched_to_off += 1
                    total += 1

                mixed = _summarize(selected)
                row = {
                    "crossover_weight": crossover_weight,
                    "floor_shadow_margin": floor_margin,
                    "confidence_budget": confidence_budget,
                    "effective_floor_shadow": floor_shadow,
                    "switched_to_router_off_cases": switched_to_off,
                    "crossover_win_cases": crossover_win_cases,
                    "floor_shadow_blocked_cases": floor_shadow_blocked,
                    "confidence_blocked_cases": confidence_blocked,
                    "switched_ratio": (switched_to_off / total) if total else 0.0,
                    "metrics": mixed,
                    "delta_vs_baseline": {
                        "saving": mixed["global_token_saving_rate"] - baseline["global_token_saving_rate"],
                        "jaccard": mixed["avg_reconstruction_fidelity_jaccard"] - baseline["avg_reconstruction_fidelity_jaccard"],
                        "integrity": mixed["avg_sensitive_integrity"] - baseline["avg_sensitive_integrity"],
                    },
                    "gate": {
                        "saving_floor_ok": mixed["global_token_saving_rate"] >= args.saving_floor,
                        "jaccard_floor_ok": mixed["avg_reconstruction_fidelity_jaccard"] >= args.jaccard_floor,
                        "integrity_floor_ok": mixed["avg_sensitive_integrity"] >= args.integrity_floor,
                    },
                }
                runs.append(row)

    viable = [r for r in runs if all(r["gate"].values())]
    recommended = (
        sorted(
            viable,
            key=lambda r: (
                r["metrics"]["avg_reconstruction_fidelity_jaccard"],
                r["metrics"]["global_token_saving_rate"],
            ),
            reverse=True,
        )[0]
        if viable
        else None
    )
    decision = "GO_W18_E3_COUPLED_VETO_DOMAIN_BUDGET" if recommended else "HOLD_W18_E2_NO_VIABLE"

    out_doc = {
        "schema": "track_a_week18_budgeted_crossover_shadow_sweep_v1",
        "generated_at_utc": _now_utc(),
        "inputs": {
            "input": str(args.input),
            "active_a_report": str(args.active_a_report),
            "pack": str(args.pack),
            "crossover_weight_grid": crossover_weights,
            "floor_shadow_margin_grid": floor_margins,
            "confidence_budget_grid": confidence_budgets,
            "caps": {"general": gc, "sensitive": sc, "hangul": hc},
            "floors": {
                "saving_floor": args.saving_floor,
                "jaccard_floor": args.jaccard_floor,
                "integrity_floor": args.integrity_floor,
            },
        },
        "baseline_router_on": baseline,
        "run_count": len(runs),
        "viable_count": len(viable),
        "recommended": recommended,
        "decision": decision,
        "next_action": (
            "Proceed to W18-E3 coupled veto domain-budget sweep."
            if decision == "GO_W18_E3_COUPLED_VETO_DOMAIN_BUDGET"
            else "Keep baseline and continue to W18-E3 path with HOLD evidence."
        ),
        "runs": sorted(
            runs,
            key=lambda r: (
                r["metrics"]["avg_reconstruction_fidelity_jaccard"],
                r["metrics"]["global_token_saving_rate"],
            ),
            reverse=True,
        ),
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "decision": decision, "viable_count": len(viable)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
