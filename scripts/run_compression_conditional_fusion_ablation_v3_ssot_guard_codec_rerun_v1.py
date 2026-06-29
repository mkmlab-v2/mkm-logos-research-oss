#!/usr/bin/env python3
"""[HYPO] Conditional fusion ablation v3 — SSOT-only knee_j_guard (recommended policy).

Reuses v2 codec caches; only zone_d_ssot bleed cases route to knee_j codec arm.
No ACTIVE write · send_gate HOLD · apply_forbidden.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_compression_conditional_fusion_ablation_v1 import (  # noqa: E402
    pick_policy_ssot_only,
)
from scripts.run_compression_conditional_fusion_ablation_v2_codec_rerun_v1 import (  # noqa: E402
    INPUT_V2,
    build,
)

DEFAULT_OUT = ROOT / "reports/compression_conditional_fusion_ablation_v3_ssot_guard_v1_latest.json"
V2_OUT = ROOT / "reports/compression_conditional_fusion_ablation_v2_codec_rerun_v1_latest.json"
SCHEMA = "compression_conditional_fusion_ablation_v3_ssot_guard_v1"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--bench-input", type=Path, default=INPUT_V2)
    ap.add_argument("--holdout-frac", type=float, default=0.2)
    ap.add_argument(
        "--force-codec-rerun",
        action="store_true",
        help="Re-run evaluate_report arms (default: reuse v2 caches)",
    )
    args = ap.parse_args()

    skip_codec = not args.force_codec_rerun
    doc = build(
        holdout_frac=args.holdout_frac,
        skip_codec_rerun=skip_codec,
        bench_input=args.bench_input if args.bench_input.is_absolute() else ROOT / args.bench_input,
        policy_fn=pick_policy_ssot_only,
        schema=SCHEMA,
        theory_lane="compression_conditional_fusion_ssot_guard_codec_rerun",
        protocol_model="merge(active_codec, knee_j_codec) per pick_policy_ssot_only",
        v2_compare_pointer=V2_OUT,
    )
    doc["reproducible_command"] = (
        "py scripts/run_compression_conditional_fusion_ablation_v3_ssot_guard_codec_rerun_v1.py "
        f"--holdout-frac {args.holdout_frac}"
    )
    doc["recommended_policy"] = True
    doc["verdict_ko"].insert(
        0,
        "v3 SSOT-only guard — knee_j_guard only on zone_d_ssot bleed (recommended vs v2 broad guard)",
    )

    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(out_path),
                "beat_frozen": doc["beat_check_conditional_vs_frozen"].get("beat_frozen"),
                "uplift_signal_holdout": doc["uplift_signal_holdout"],
                "knee_j_guard_count": doc["policy_counts"].get("knee_j_guard"),
                "conditional_min_j": doc["golden40_codec_arms"]["conditional_merged"][
                    "min_reconstruction_fidelity_jaccard"
                ],
                "conditional_saving": doc["golden40_codec_arms"]["conditional_merged"]["global_token_saving_rate"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
