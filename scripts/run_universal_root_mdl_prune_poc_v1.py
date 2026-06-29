#!/usr/bin/env python3
"""Layer C MDL lexicon prune PoC — Golden-40 Jaccard sweep 5/10/15% [HYPO]."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.master_codebook_lexicon_v1_bridge import resolve_latest_codebook_path  # noqa: E402
from scripts.universal_root_mdl_prune_lib_v1 import (  # noqa: E402
    DEFAULT_JACCARD_FLOOR_DELTA_PP,
    DEFAULT_SWEEP_PCTS,
    run_mdl_sweep,
)

DEFAULT_OUT = ROOT / "reports/universal_root_mdl_prune_poc_v1_latest.json"
DEFAULT_SCRATCH = ROOT / "reports/constitution/btrack_pilot/_mdl_prune_poc_scratch"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline-lexicon", type=Path, default=None)
    ap.add_argument("--scratch-dir", type=Path, default=DEFAULT_SCRATCH)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--sweep-pcts", default="5,10,15", help="Comma-separated reduction targets")
    ap.add_argument(
        "--jaccard-floor-delta-pp",
        type=float,
        default=DEFAULT_JACCARD_FLOOR_DELTA_PP,
        help="Min Jaccard = baseline - this (default 0.005 = 0.5pp)",
    )
    ap.add_argument("--strict", action="store_true", help="Exit 1 if no sweep passes PoC gate")
    args = ap.parse_args()

    baseline = args.baseline_lexicon
    if baseline is None:
        resolved = resolve_latest_codebook_path()
        if resolved is None:
            print("ABORT: baseline lexicon not found", file=sys.stderr)
            return 2
        baseline = resolved
    if not baseline.is_file():
        print(f"ABORT: missing baseline {baseline}", file=sys.stderr)
        return 2

    sweep_pcts = tuple(float(x.strip()) for x in args.sweep_pcts.split(",") if x.strip())
    result = run_mdl_sweep(
        baseline,
        sweep_pcts=sweep_pcts,
        jaccard_floor_delta_pp=args.jaccard_floor_delta_pp,
        scratch_dir=args.scratch_dir,
    )

    report = {
        "schema": "universal_root_mdl_prune_poc_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_promotion_forbidden": True,
        **result,
        "gate": {
            "min_reduction_pct": 5.0,
            "max_reduction_pct": 15.0,
            "jaccard_floor_delta_pp": args.jaccard_floor_delta_pp,
            "any_sweep_pass": result.get("any_sweep_pass"),
        },
        "reproduce": "py scripts/run_universal_root_mdl_prune_poc_v1.py",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ok = bool(result.get("any_sweep_pass"))
    print(
        json.dumps(
            {
                "ok": ok,
                "out": str(args.out),
                "baseline_jaccard": result.get("baseline_jaccard"),
                "any_sweep_pass": ok,
                "best_reduction_pct": (result.get("best_sweep") or {}).get("prune_meta", {}).get(
                    "actual_reduction_pct"
                ),
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok or not args.strict else 1


if __name__ == "__main__":
    raise SystemExit(main())
