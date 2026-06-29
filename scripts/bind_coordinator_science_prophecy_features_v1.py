#!/usr/bin/env python3
"""[HYPO] Thin manifest: coordinator science kernel -> general_prophecy B-track features (no L1 merge)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
KERNEL_SPEC = (
    ROOT / "experiments/nextgen_clean_slate_cpu_v1/COORDINATOR_SCIENCE_KERNEL_V2.json"
)
SWEEP_DEFAULT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_coordinator_science_loss_sweep_v1_latest.json"
)
OUT_DEFAULT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/coordinator_prophecy_feature_binding_v1_latest.json"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_forbidden(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return [str(x) for x in raw]
    return [str(raw)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kernel-spec", type=Path, default=KERNEL_SPEC)
    ap.add_argument("--sweep-json", type=Path, default=SWEEP_DEFAULT)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    ap.add_argument(
        "--run-eval-chain",
        action="store_true",
        help="Also subprocess run_prophecy_btrack_recommended_eval_chain_v1.py (slow)",
    )
    args = ap.parse_args()

    spec = json.loads(args.kernel_spec.read_text(encoding="utf-8-sig"))
    sweep = (
        json.loads(args.sweep_json.read_text(encoding="utf-8-sig"))
        if args.sweep_json.is_file()
        else None
    )
    best = (sweep or {}).get("best_dual_axis_beat") or (sweep or {}).get("best_by_loss")

    features = [
        {
            "name": "coordinator_lens_disagreement_avg",
            "source": "ng40_coordinator_science_loss_sweep",
            "role": "uncertainty_proxy",
        },
        {
            "name": "coordinator_science_weight_scale",
            "source": "sweep_best_row",
            "role": "science_kernel_knob",
        },
        {
            "name": "fusion_rationale_strength_delta",
            "source": "build_general_prophecy_explainable_v1.fusion_decision",
            "role": "optional_weight_tweak_HYPO",
        },
    ]

    out: dict[str, Any] = {
        "schema": "coordinator_prophecy_feature_binding_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "mode": "thin_manifest_only",
        "kernel_spec": str(args.kernel_spec.relative_to(ROOT)).replace("\\", "/"),
        "sweep_pointer": (
            str(args.sweep_json.relative_to(ROOT)).replace("\\", "/")
            if args.sweep_json.is_file()
            else None
        ),
        "sweep_best_row": best,
        "proposed_features": features,
        "eval_chain_pointer": (
            spec.get("prophecy_binding", {}).get("eval_chain_pointer")
        ),
        "forbidden": _normalize_forbidden(
            spec.get("prophecy_binding", {}).get("forbidden")
        ),
        "note_ko": "BLS 6/6 전 밤: 피처 정의만 고정. L1·NG-40 코덱 합선 없음.",
    }

    if args.run_eval_chain:
        import subprocess
        import sys

        chain = ROOT / "scripts/run_prophecy_btrack_recommended_eval_chain_v1.py"
        cp = subprocess.run(
            [sys.executable, str(chain), "--help"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        out["eval_chain_probe"] = {
            "script": str(chain.relative_to(ROOT)).replace("\\", "/"),
            "help_exit_code": cp.returncode,
            "note": "Full AB not auto-run; invoke chain manually before BLS",
        }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"wrote": str(args.out_json), "features": len(features)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
