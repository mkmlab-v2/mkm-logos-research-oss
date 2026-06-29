#!/usr/bin/env python3
"""RQ-026 matrix variant × holdout-fraction sweep ([HYPO], experiments/ only)."""
from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "experiments/sasang_temperament_agents_v1/specs"
DEFAULT_SPEC = SPECS / "temperament_agent_state_v1.example.json"
DEFAULT_INPUT = ROOT / "reports/btrack_per_date_directions_market_psych_v2.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/sasang_temperament_agents_matrix_sweep_v1_latest.json"
REPORT_OUT = ROOT / "reports/sasang_temperament_agents_matrix_sweep_v1_latest.json"

MATRIX_VARIANTS: list[tuple[str, Path]] = [
    ("v1_1", SPECS / "pathology_transition_matrix_v1_1.json"),
    ("v1_2", SPECS / "pathology_transition_matrix_v1_2.json"),
]
DEFAULT_FRACTIONS = (0.1, 0.2, 0.3)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_phase4():
    p = ROOT / "scripts/build_sasang_temperament_agents_phase4_holdout_ablation_v1.py"
    spec = importlib.util.spec_from_file_location("rq026_phase4", p)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import phase4: {p}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _row_summary(variant: str, matrix_path: Path, frac: float, doc: dict[str, Any]) -> dict[str, Any]:
    hold_m = (doc.get("matrix_coupled") or {}).get("holdout_eval_axes") or {}
    hold_n = (doc.get("no_matrix_legacy") or {}).get("holdout_eval_axes") or {}
    delta = doc.get("ablation_delta_holdout") or {}
    gates = doc.get("holdout_gates") or {}
    dom_m = hold_m.get("constitution_pathology_dominance") or {}
    return {
        "matrix_variant": variant,
        "matrix_path": str(matrix_path.relative_to(ROOT)).replace("\\", "/"),
        "matrix_version": _load(matrix_path).get("version"),
        "holdout_fraction": frac,
        "n_days_holdout": doc.get("n_days_holdout"),
        "holdout_consistency_matrix": (hold_m.get("temperament_consistency") or {}).get("score"),
        "holdout_consistency_no_matrix": (hold_n.get("temperament_consistency") or {}).get("score"),
        "delta_consistency_matrix_minus_none": delta.get("temperament_consistency_matrix_minus_none"),
        "holdout_fear_dominance_rate_matrix": dom_m.get(
            "fear_constitution_dominant_on_aggravating_rate"
        ),
        "holdout_fear_dominance_pass_matrix": gates.get("matrix_coupled_pass"),
        "holdout_both_pass": gates.get("both_pass"),
    }


def _pick_recommended(rows: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [r for r in rows if r.get("holdout_both_pass") is True]
    if not eligible:
        return {"variant": None, "holdout_fraction": None, "reason_ko": "both_pass 행 없음"}
    # Prefer smallest |delta| to no-matrix (matrix adds value without hurting consistency)
    best = min(
        eligible,
        key=lambda r: abs(float(r.get("delta_consistency_matrix_minus_none") or 0)),
    )
    return {
        "variant": best.get("matrix_variant"),
        "holdout_fraction": best.get("holdout_fraction"),
        "delta_consistency_matrix_minus_none": best.get("delta_consistency_matrix_minus_none"),
        "reason_ko": "holdout both_pass 중 matrix−none consistency Δ 절대값 최소.",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--also-report", action="store_true")
    ap.add_argument(
        "--fractions",
        default=",".join(str(x) for x in DEFAULT_FRACTIONS),
        help="comma-separated holdout fractions e.g. 0.1,0.2,0.3",
    )
    args = ap.parse_args()

    fractions = [float(x.strip()) for x in args.fractions.split(",") if x.strip()]
    for f in fractions:
        if not 0.05 <= f <= 0.5:
            raise SystemExit(f"invalid holdout fraction: {f}")

    if not args.spec.is_file() or not args.input.is_file():
        raise SystemExit("missing spec or input")

    phase4 = _load_phase4()
    spec = _load(args.spec)
    env_doc = _load(args.input)
    env_rows = [r for r in env_doc.get("rows") or [] if isinstance(r, dict)]
    if not env_rows:
        raise SystemExit("no environment rows")
    run_sim = phase4._load_run_sim()

    sweep_rows: list[dict[str, Any]] = []
    for variant, matrix_path in MATRIX_VARIANTS:
        if not matrix_path.is_file():
            raise SystemExit(f"missing matrix variant: {matrix_path}")
        matrix = _load(matrix_path)
        for frac in fractions:
            doc = phase4.build(
                spec=spec,
                matrix=matrix,
                env_rows=env_rows,
                holdout_fraction=frac,
                run_sim=run_sim,
            )
            sweep_rows.append(_row_summary(variant, matrix_path, frac, doc))

    recommended = _pick_recommended(sweep_rows)
    doc_out: dict[str, Any] = {
        "schema": "sasang_temperament_agents_matrix_sweep_v1",
        "generated_at_utc": _utc(),
        "rq_id": "RQ-026",
        "hypothesis_tier": "B",
        "research_only": True,
        "not_promoted_track_a": True,
        "fractions": fractions,
        "variants": [v for v, _ in MATRIX_VARIANTS],
        "rows": sweep_rows,
        "recommended_candidate": recommended,
        "verdict_ko": (
            f"권장 후보 matrix {recommended.get('variant')} @ holdout {recommended.get('holdout_fraction')}"
            if recommended.get("variant")
            else "both_pass 없음 — matrix 튜닝 재검토."
        ),
        "note_ko": "sim/mechanics sweep only; CLOSED·Track A·임상 단정 없음.",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.out)
    if args.also_report:
        REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
        REPORT_OUT.write_text(json.dumps(doc_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(REPORT_OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
