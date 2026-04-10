#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ARTIFACTS / "trackb_quaternion_two_stage_gate_v2.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_curve(doc: dict[str, Any]) -> list[dict[str, Any]]:
    curve = doc.get("curve")
    if isinstance(curve, list):
        return [c for c in curve if isinstance(c, dict)]
    best = doc.get("best")
    if isinstance(best, dict) and isinstance(best.get("curve"), list):
        return [c for c in best.get("curve", []) if isinstance(c, dict)]
    top5 = doc.get("top5")
    if isinstance(top5, list) and top5:
        first = top5[0]
        if isinstance(first, dict) and isinstance(first.get("curve"), list):
            return [c for c in first.get("curve", []) if isinstance(c, dict)]
    return []


def _curve_rate(row: dict[str, Any]) -> float:
    if "decode_exact_rate" in row:
        return float(row.get("decode_exact_rate", 0.0))
    if "exact_sequence_match_rate" in row:
        return float(row.get("exact_sequence_match_rate", 0.0))
    if "token_set_match_rate" in row:
        return float(row.get("token_set_match_rate", 0.0))
    return 0.0


def _curve_collision(row: dict[str, Any]) -> float:
    if "collision_rate" in row:
        return float(row.get("collision_rate", 0.0))
    if "collision_count" in row and "sample_count" in row:
        n = float(row.get("sample_count", 0.0))
        c = float(row.get("collision_count", 0.0))
        return 0.0 if n <= 0 else c / n
    return 0.0


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build two-stage gate report for Track B quaternion experiments.")
    ap.add_argument("--order-path", type=Path, default=ARTIFACTS / "trackb_quaternion_order_experiment_v1.json")
    ap.add_argument("--stress-path", type=Path, default=ARTIFACTS / "trackb_quaternion_order_stress_v1.json")
    ap.add_argument("--generalization-path", type=Path, default=ARTIFACTS / "trackb_quaternion_generalization_v1.json")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--closed-min-exact-rate", type=float, default=0.999)
    ap.add_argument("--open-min-exact-rate", type=float, default=0.995)
    ap.add_argument("--open-max-collision-rate", type=float, default=0.01)
    args = ap.parse_args()

    order_doc = _load_json(args.order_path)
    stress_doc = _load_json(args.stress_path)
    gen_doc = _load_json(args.generalization_path)

    order_rate = float(order_doc.get("pair_decode_exact_rate", 0.0))
    stress_rate = float(stress_doc.get("min_decode_exact_rate", 0.0))

    curve = _extract_curve(gen_doc)
    if curve:
        worst_exact = min(_curve_rate(row) for row in curve)
        worst_collision = max(_curve_collision(row) for row in curve)
        worst_exact_cell = min(curve, key=lambda r: _curve_rate(r))
        worst_collision_cell = max(curve, key=lambda r: _curve_collision(r))
    else:
        worst_exact = 0.0
        worst_collision = 1.0
        worst_exact_cell = None
        worst_collision_cell = None

    stage1_pass = (order_rate >= args.closed_min_exact_rate) and (stress_rate >= args.closed_min_exact_rate)
    stage2_pass = (worst_exact >= args.open_min_exact_rate) and (worst_collision <= args.open_max_collision_rate)
    decision = "GO" if stage1_pass and stage2_pass else "NO_GO"

    out = {
        "schema": "trackb_quaternion_two_stage_gate_v2",
        "generated_at_utc": _utc_now_iso(),
        "gate_profile": "trackb_quaternion_restore_research_v2",
        "research_only": True,
        "not_billing_claim": True,
        "inputs": {
            "order_experiment": str(args.order_path.resolve()),
            "order_stress": str(args.stress_path.resolve()),
            "generalization": str(args.generalization_path.resolve()),
        },
        "thresholds": {
            "closed_min_exact_rate": args.closed_min_exact_rate,
            "open_min_exact_rate": args.open_min_exact_rate,
            "open_max_collision_rate": args.open_max_collision_rate,
        },
        "stages": {
            "stage1_closed_candidate_set": {
                "description": "Closed candidate pool exact decode stability.",
                "pair_decode_exact_rate": order_rate,
                "stress_min_decode_exact_rate": stress_rate,
                "pass": stage1_pass,
            },
            "stage2_open_generalization": {
                "description": "Length/OOV mixed pool robustness (open-style benchmark).",
                "worst_decode_exact_rate": worst_exact,
                "worst_collision_rate": worst_collision,
                "worst_exact_cell": worst_exact_cell,
                "worst_collision_cell": worst_collision_cell,
                "pass": stage2_pass,
            },
        },
        "decision": decision,
        "policy_notes": [
            "Research validation report only; not a production readiness certificate.",
            "Closed-pool NN success and open-style robustness are split to prevent over-claiming.",
            "Promotion to production requires separate tests and governance gates.",
            "This gate does not authorize production billing/VRAM claims.",
        ],
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "decision": decision, "out": str(args.out.resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
