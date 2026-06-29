#!/usr/bin/env python3
"""[HYPO] RQ-024 v1 triangular validation: single holdout + multisplit + blocked WF."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_HOLDOUT = ROOT / "reports/rq024_btc_lens_feature_v0_blind_holdout_v1_latest.json"
DEFAULT_MULTISPLIT = ROOT / "reports/rq024_btc_lens_feature_v0_multisplit_v1_latest.json"
DEFAULT_WF = ROOT / "reports/rq024_btc_lens_feature_v0_wf_ablation_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/rq024_btc_lens_v1_triangular_validation_v1_latest.json"
SCHEMA = "rq024_btc_lens_v1_triangular_validation_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--holdout-json", type=Path, default=DEFAULT_HOLDOUT)
    ap.add_argument("--multisplit-json", type=Path, default=DEFAULT_MULTISPLIT)
    ap.add_argument("--wf-json", type=Path, default=DEFAULT_WF)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    holdout = _load(args.holdout_json if args.holdout_json.is_absolute() else ROOT / args.holdout_json)
    multisplit = _load(args.multisplit_json if args.multisplit_json.is_absolute() else ROOT / args.multisplit_json)
    wf = _load(args.wf_json if args.wf_json.is_absolute() else ROOT / args.wf_json)

    v1_holdout = bool((holdout.get("dod_v1") or {}).get("met"))
    v1_multisplit = bool((multisplit.get("dod_multisplit_v1") or {}).get("met"))
    v1_wf = bool((wf.get("dod_wf_ablation") or {}).get("best_v1_mean_beats_052"))

    legs = {
        "single_50_50_holdout": {
            "pass": v1_holdout,
            "accuracy": next(
                (
                    (v.get("test_blind") or {}).get("accuracy")
                    for v in (holdout.get("variants") or [])
                    if v.get("slug") == "rq024_causal_lens_v1"
                ),
                None,
            ),
            "artifact": str(DEFAULT_HOLDOUT.relative_to(ROOT)).replace("\\", "/"),
        },
        "multisplit_chronological": {
            "pass": v1_multisplit,
            "mean_accuracy": (multisplit.get("aggregate") or {}).get("rq024_causal_lens_v1", {}).get(
                "mean_blind_test_accuracy"
            ),
            "fraction_beats_052": (multisplit.get("aggregate") or {})
            .get("rq024_causal_lens_v1", {})
            .get("fraction_beats_ceiling_052"),
            "artifact": str(DEFAULT_MULTISPLIT.relative_to(ROOT)).replace("\\", "/"),
        },
        "blocked_walkforward": {
            "pass": v1_wf,
            "best_v1_mean": (wf.get("best_v1_by_mean_test_accuracy") or {}).get("v1_aggregate", {}).get(
                "mean_test_accuracy"
            ),
            "best_nf": (wf.get("best_v1_by_mean_test_accuracy") or {}).get("n_folds"),
            "artifact": str(DEFAULT_WF.relative_to(ROOT)).replace("\\", "/"),
        },
    }

    pass_count = sum(1 for leg in legs.values() if leg.get("pass"))
    triangle_met = pass_count == 3

    final_action = "WATCH"
    if triangle_met:
        final_action = "WATCH_V1_TRIANGLE"
    elif pass_count == 2:
        final_action = "WATCH_V1_PARTIAL"
    elif v1_wf:
        final_action = "WATCH_V1_WF"

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "rq_id": "RQ-024",
        "overlay_version": "v1",
        "promotion_axis": "no_expanded_prior",
        "legs": legs,
        "triangle": {
            "pass_count": pass_count,
            "required": 3,
            "met": triangle_met,
            "note": "All three protocols must pass 0.52 mean/fraction rules for v1 — still not Track A / 0.55 / combined.",
        },
        "final_action": final_action,
        "forbidden": [
            "Track A promotion from triangle pass alone",
            "merge KOSPI flow [NON_GATING] into this verdict",
            "expanded-prior promotion axis",
        ],
    }

    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path.resolve()}")
    print(f"triangle_met={triangle_met} pass_count={pass_count} final_action={final_action}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
