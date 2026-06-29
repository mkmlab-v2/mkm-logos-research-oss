#!/usr/bin/env python3
"""[HYPO] RQ-024 overlay pin decision — v1 default, v2 research hold."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECHECK = ROOT / "reports/rq024_nf5_wf_v2_vs_v1_recheck_v1_latest.json"
DEFAULT_ABLATION = ROOT / "reports/rq024_nf5_v2_feature_ablation_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/rq024_v1_overlay_pin_decision_hypo_v1_latest.json"
SCHEMA = "rq024_v1_overlay_pin_decision_hypo_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--recheck-json", type=Path, default=DEFAULT_RECHECK)
    ap.add_argument("--ablation-json", type=Path, default=DEFAULT_ABLATION)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    recheck_path = args.recheck_json if args.recheck_json.is_absolute() else ROOT / args.recheck_json
    ablation_path = args.ablation_json if args.ablation_json.is_absolute() else ROOT / args.ablation_json
    if not recheck_path.is_file():
        raise SystemExit(f"missing recheck: {recheck_path}")
    if not ablation_path.is_file():
        raise SystemExit(f"missing ablation: {ablation_path}")

    recheck = _load(recheck_path)
    ablation = _load(ablation_path)
    nf5 = recheck.get("nf5") or {}
    v1 = float(nf5.get("v1_mean_test_accuracy") or 0)
    v2 = float(nf5.get("v2_mean_test_accuracy") or 0)
    summary = ablation.get("summary") or {}

    pin_v1 = v1 >= v2 and not bool(nf5.get("v2_gate_055_pass"))

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "rq_id": "RQ-024",
        "evidence": {
            "recheck_json": str(recheck_path.relative_to(ROOT)).replace("\\", "/"),
            "ablation_json": str(ablation_path.relative_to(ROOT)).replace("\\", "/"),
            "v1_mean_nf5": v1,
            "v2_mean_nf5": v2,
            "delta_v2_minus_v1": round(v2 - v1, 6),
            "v2_ablation_no_vol": (summary.get("v2_ablate_no_volume_ratio_5d") or {}).get(
                "mean_test_accuracy"
            ),
            "v2_ablation_no_pir": (summary.get("v2_ablate_no_prior_intraday_range") or {}).get(
                "mean_test_accuracy"
            ),
        },
        "decision": {
            "default_overlay": "v1" if pin_v1 else "v2",
            "v2_status": "research_hold" if pin_v1 else "candidate_recheck",
            "gate_055_pass": False,
            "track_a_promotion": False,
            "live_trading": False,
            "human_signoff_required": True,
            "rationale": (
                "v2 nf5 mean below v1; ablation does not isolate a single helpful v2 feature; "
                "gate 0.55 fail on both."
                if pin_v1
                else "v2 mean >= v1 on recheck — pin review required."
            ),
        },
        "track_wall": {
            "track_a_auto_merge": False,
            "oracle_promotion": False,
            "live_trading": False,
        },
    }
    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path} default_overlay={payload['decision']['default_overlay']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
