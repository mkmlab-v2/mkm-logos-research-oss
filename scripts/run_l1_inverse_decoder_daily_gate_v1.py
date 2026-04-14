#!/usr/bin/env python3
"""Daily gate for L1 inverse decoder commercialization health.

Checks objective-v4 default path on:
- mixed mode non-regression floor
- swap_typo absolute floor
- swap_typo resilience floor

Outputs:
- docs/final/artifacts/l1_inverse_decoder_daily_gate_v1_latest.json
- reports/l1_inverse_decoder_daily_gate_log_v1.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_l1_inverse_decoder_spike_test import run

ART = ROOT / "docs" / "final" / "artifacts"
OUT_DEFAULT = ART / "l1_inverse_decoder_daily_gate_v1_latest.json"
LOG_DEFAULT = ROOT / "reports" / "l1_inverse_decoder_daily_gate_log_v1.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_seeds(raw: str) -> list[int]:
    out = [int(x.strip()) for x in raw.split(",") if x.strip()]
    if not out:
        raise ValueError("seeds must not be empty")
    return out


def _eval_mode(
    *,
    seeds: list[int],
    samples: int,
    beam_size: int,
    noise_level: float,
    scoring_mode: str,
    forced_mode: str | None,
) -> dict[str, Any]:
    exact_vals: list[float] = []
    recovery_vals: list[float] = []
    for seed in seeds:
        rep, _ = run(
            seed=seed,
            samples=samples,
            beam_size=beam_size,
            noise_level=noise_level,
            scoring_mode=scoring_mode,
            forced_noise_mode=forced_mode,
            swap_typo_objective_v4=True,
        )
        exact_vals.append(float(rep["exact_restore_rate"]))
        recovery_vals.append(float(rep["recovery_rate"]))
    return {
        "mode": forced_mode or "mixed",
        "avg_exact_restore_rate": sum(exact_vals) / len(exact_vals),
        "avg_recovery_rate": sum(recovery_vals) / len(recovery_vals),
        "min_exact_restore_rate": min(exact_vals),
        "min_recovery_rate": min(recovery_vals),
        "per_seed": [
            {"seed": seeds[i], "exact_restore_rate": exact_vals[i], "recovery_rate": recovery_vals[i]}
            for i in range(len(seeds))
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds", type=str, default="701,809")
    ap.add_argument("--samples", type=int, default=120)
    ap.add_argument("--beam-size", type=int, default=8)
    ap.add_argument("--noise-level", type=float, default=0.1)
    ap.add_argument("--scoring-mode", choices=("legacy", "enhanced", "swap_v2"), default="enhanced")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--log", type=Path, default=LOG_DEFAULT)
    ap.add_argument(
        "--mode",
        choices=("warning", "block"),
        default="warning",
        help="block: return non-zero when any gate fails",
    )
    args = ap.parse_args()

    seeds = _parse_seeds(args.seeds)
    mixed = _eval_mode(
        seeds=seeds,
        samples=args.samples,
        beam_size=args.beam_size,
        noise_level=args.noise_level,
        scoring_mode=args.scoring_mode,
        forced_mode=None,
    )
    swap_typo = _eval_mode(
        seeds=seeds,
        samples=args.samples,
        beam_size=args.beam_size,
        noise_level=args.noise_level,
        scoring_mode=args.scoring_mode,
        forced_mode="swap_typo",
    )

    # Daily guardrails (commercial readiness aligned)
    thresholds = {
        "mixed_exact_min": 0.55,
        "mixed_recovery_min": 0.58,
        "swap_typo_exact_min": 0.25,
        "swap_typo_recovery_min": 0.29,
    }
    checks = {
        "mixed_exact_ok": mixed["avg_exact_restore_rate"] >= thresholds["mixed_exact_min"],
        "mixed_recovery_ok": mixed["avg_recovery_rate"] >= thresholds["mixed_recovery_min"],
        "swap_typo_exact_ok": swap_typo["avg_exact_restore_rate"] >= thresholds["swap_typo_exact_min"],
        "swap_typo_recovery_ok": swap_typo["avg_recovery_rate"] >= thresholds["swap_typo_recovery_min"],
    }
    all_ok = all(checks.values())

    out_doc: dict[str, Any] = {
        "schema": "l1_inverse_decoder_daily_gate_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "inputs": {
            "seeds": seeds,
            "samples": args.samples,
            "beam_size": args.beam_size,
            "noise_level": args.noise_level,
            "scoring_mode": args.scoring_mode,
            "swap_typo_objective_v4_default": True,
        },
        "results": {"mixed": mixed, "swap_typo": swap_typo},
        "thresholds": thresholds,
        "checks": checks,
        "gate": {
            "all_ok": all_ok,
            "decision": "GO_KEEP_OBJECTIVE_V4_DEFAULT_ON" if all_ok else "HOLD_INVESTIGATE",
            "mode": args.mode,
        },
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    log_path = args.log if args.log.is_absolute() else ROOT / args.log
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_line = {
        "ts_utc": out_doc["generated_at_utc"],
        "schema": "l1_inverse_decoder_daily_gate_log_v1",
        "decision": out_doc["gate"]["decision"],
        "all_ok": out_doc["gate"]["all_ok"],
        "mixed_exact": mixed["avg_exact_restore_rate"],
        "mixed_recovery": mixed["avg_recovery_rate"],
        "swap_typo_exact": swap_typo["avg_exact_restore_rate"],
        "swap_typo_recovery": swap_typo["avg_recovery_rate"],
        "out": str(out_path),
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(log_line, ensure_ascii=False) + "\n")

    exit_code = 0
    if args.mode == "block" and not all_ok:
        exit_code = 1

    print(
        json.dumps(
            {
                "ok": exit_code == 0,
                "out": str(out_path),
                "decision": out_doc["gate"]["decision"],
                "checks": checks,
            },
            ensure_ascii=False,
        )
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
