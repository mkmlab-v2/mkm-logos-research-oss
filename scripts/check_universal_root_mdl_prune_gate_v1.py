#!/usr/bin/env python3
"""Gate check for universal_root_mdl_prune_poc report vs UNIVERSAL_ROOT_GATE_SPEC [HYPO]."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POC = ROOT / "reports/universal_root_mdl_prune_poc_v1_latest.json"
DEFAULT_SPEC = ROOT / "docs/final/artifacts/UNIVERSAL_ROOT_GATE_SPEC_V1.json"
DEFAULT_OUT = ROOT / "reports/universal_root_mdl_prune_gate_v1_latest.json"


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def evaluate_gate(poc: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    thr = (
        (spec.get("promotion_gates") or {})
        .get("planes", {})
        .get("layer_c_mdl", {})
        .get("thresholds", {})
    )
    min_red = float(thr.get("min_row_reduction_pct", 5.0))
    max_red = float(thr.get("max_row_reduction_pct", 15.0))
    jaccard_delta_floor = float(thr.get("min_jaccard_delta_pp", 0.0))

    passing = [r for r in (poc.get("sweep_rows") or []) if r.get("pass_poc")]
    best = poc.get("best_sweep") or {}
    prune_meta = best.get("prune_meta") or {}
    actual_red = float(prune_meta.get("actual_reduction_pct") or 0.0)
    delta_pp = float(best.get("jaccard_delta_pp_vs_baseline") or 0.0)

    checks = [
        {
            "name": "any_sweep_pass",
            "ok": bool(poc.get("any_sweep_pass")),
            "observed": poc.get("any_sweep_pass"),
        },
        {
            "name": "reduction_in_band",
            "ok": min_red <= actual_red <= max_red if passing else False,
            "observed": actual_red,
            "threshold_min": min_red,
            "threshold_max": max_red,
        },
        {
            "name": "jaccard_delta_pp_floor",
            "ok": delta_pp >= jaccard_delta_floor - 1e-9 if passing else False,
            "observed": delta_pp,
            "threshold": jaccard_delta_floor,
        },
    ]
    return {
        "gate_ok": all(c["ok"] for c in checks),
        "checks": checks,
        "passing_sweep_count": len(passing),
        "best_sweep_target_pct": best.get("sweep_reduction_pct_target"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--poc-json", type=Path, default=DEFAULT_POC)
    ap.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.poc_json.is_file():
        print(json.dumps({"ok": False, "error": "missing_poc_report"}))
        return 2

    poc = _read(args.poc_json)
    spec = _read(args.spec) if args.spec.is_file() else {}
    gate = evaluate_gate(poc, spec)
    out_doc = {
        "schema": "universal_root_mdl_prune_gate_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "poc_pointer": str(args.poc_json.relative_to(ROOT)).replace("\\", "/"),
        **gate,
        "reproduce": "py scripts/check_universal_root_mdl_prune_gate_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": gate["gate_ok"], "out": str(args.out)}, ensure_ascii=False))
    return 0 if gate["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
