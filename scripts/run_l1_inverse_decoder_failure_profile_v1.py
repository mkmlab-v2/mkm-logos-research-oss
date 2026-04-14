#!/usr/bin/env python3
"""Build failure-profile report for L1 inverse decoder (v4 baseline)."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_l1_inverse_decoder_spike_test import _extract_literal_channel, run

ART = ROOT / "docs" / "final" / "artifacts"
OUT_DEFAULT = ART / "l1_inverse_decoder_failure_profile_v1_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_seeds(raw: str) -> list[int]:
    vals = [int(x.strip()) for x in raw.split(",") if x.strip()]
    if not vals:
        raise ValueError("empty seeds")
    return vals


def _classify(row: dict[str, Any]) -> str:
    src = row["source"].split()
    rst = row["restored"].split()
    noisy = row["noisy"].split()
    lit = _extract_literal_channel(src)
    if any(i >= len(rst) or rst[i] != tok for i, tok in lit.items()):
        return "literal_anchor_mismatch"
    if len(src) != len(rst):
        return "length_mismatch"
    if Counter(src) == Counter(rst):
        return "order_only_mismatch"
    if any("X" in t or t == "OOV_TOKEN" for t in noisy):
        return "typo_oov_not_recovered"
    return "other_semantic_mismatch"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds", type=str, default="701,809,907")
    ap.add_argument("--samples", type=int, default=180)
    ap.add_argument("--beam-size", type=int, default=8)
    ap.add_argument("--noise-level", type=float, default=0.1)
    ap.add_argument("--scoring-mode", choices=("legacy", "enhanced", "swap_v2"), default="enhanced")
    ap.add_argument("--mode", choices=("mixed", "swap_typo"), default="swap_typo")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    seeds = _parse_seeds(args.seeds)
    forced_mode = None if args.mode == "mixed" else args.mode
    fail_counter: Counter[str] = Counter()
    near_miss = 0
    hard_fail = 0
    exact_vals: list[float] = []
    recovery_vals: list[float] = []

    for seed in seeds:
        rep, fails = run(
            seed=seed,
            samples=args.samples,
            beam_size=args.beam_size,
            noise_level=args.noise_level,
            scoring_mode=args.scoring_mode,
            forced_noise_mode=forced_mode,
            swap_typo_objective_v4=True,
        )
        exact_vals.append(float(rep["exact_restore_rate"]))
        recovery_vals.append(float(rep["recovery_rate"]))
        for row in fails:
            if row.get("type") == "near_miss":
                near_miss += 1
            elif row.get("type") == "hard_fail":
                hard_fail += 1
            fail_counter[_classify(row)] += 1

    total_fails = near_miss + hard_fail
    out_doc = {
        "schema": "l1_inverse_decoder_failure_profile_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "inputs": {
            "seeds": seeds,
            "samples": args.samples,
            "beam_size": args.beam_size,
            "noise_level": args.noise_level,
            "scoring_mode": args.scoring_mode,
            "mode": args.mode,
            "swap_typo_objective_v4": True,
        },
        "aggregate": {
            "avg_exact_restore_rate": sum(exact_vals) / len(exact_vals),
            "avg_recovery_rate": sum(recovery_vals) / len(recovery_vals),
            "total_failures": total_fails,
            "near_miss_count": near_miss,
            "hard_fail_count": hard_fail,
        },
        "failure_types": [
            {
                "type": k,
                "count": v,
                "ratio": (v / total_fails) if total_fails else 0.0,
            }
            for k, v in fail_counter.most_common()
        ],
    }

    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out), "top_failure": out_doc["failure_types"][:1]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
