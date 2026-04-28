# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.9, K:0.6, M:0.3}
# Balance: 88
# Purpose: Emit latency/quality baseline using the same harness as mode-router v3 longsample gate (beam-only swap_typo).
# Keywords: l1, inverse-decoder, baseline, longsample, harness
#!/usr/bin/env python3
"""Regenerate baseline JSON for run_l1_swap_typo_mode_router_decoder_v3_longsample_gate.py.

swap_typo row uses swap_typo_expand=False (beam pool only), matching pre-expansion cost profile.
mixed row uses the standard mixed path (same as gate).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_l1_swap_typo_mode_router_decoder_v3_longsample_gate import _parse_seeds, _run_mode

ART = ROOT / "docs" / "final" / "artifacts"
OUT_DEFAULT = ART / "l1_inverse_decoder_longsample_gate_harness_baseline_v1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds", type=str, default="701,809,907,1009,1103")
    ap.add_argument("--samples", type=int, default=240)
    ap.add_argument("--beam-size", type=int, default=8)
    ap.add_argument("--noise-level", type=float, default=0.1)
    ap.add_argument("--scoring-mode", choices=("legacy", "enhanced", "swap_v2"), default="enhanced")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    seeds = _parse_seeds(args.seeds)
    mixed = _run_mode(
        seeds,
        args.samples,
        args.beam_size,
        args.noise_level,
        args.scoring_mode,
        mode=None,
        swap_typo_expand=True,
    )
    swap_typo = _run_mode(
        seeds,
        args.samples,
        args.beam_size,
        args.noise_level,
        args.scoring_mode,
        mode="swap_typo",
        swap_typo_expand=False,
    )

    doc = {
        "schema": "l1_inverse_decoder_longsample_gate_harness_baseline_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "inputs": {
            "seeds": seeds,
            "samples": args.samples,
            "beam_size": args.beam_size,
            "noise_level": args.noise_level,
            "scoring_mode": args.scoring_mode,
            "swap_typo_expand": False,
            "harness_note": "swap_typo results are beam-only (swap_typo_expand=False); same loops as v3 longsample gate.",
        },
        "results": {"mixed": mixed, "swap_typo": swap_typo},
    }
    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
