#!/usr/bin/env python3
"""B-track readiness report: v5 vs v4 operational adapter (no auto-swap)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COMPARE = ROOT / "reports/myeongri_interpret_v4_v5_calibration30_diff_latest.json"
DEFAULT_V5_EVAL = ROOT / "reports/myeongri_interpret_lora_v5_eval_locked100_guard448_latest.json"
DEFAULT_V4_EVAL = ROOT / "reports/myeongri_interpret_lora_v4_eval_locked100_guard448_latest.json"
DEFAULT_V5_CLOSURE = ROOT / "reports/myeongri_interpret_v5_calibration30_closure_latest.json"
DEFAULT_STATUS = ROOT / "reports/myeongri_interpret_harness_v3_v4_status_latest.json"
DEFAULT_OUT = ROOT / "reports/myeongri_interpret_v5_operational_promotion_readiness_latest.json"

V4_ADAPTER = "storage/adapters/myeongri_interpret_lora_v0/run_interpret_v4_variant_s100"
V5_ADAPTER = "storage/adapters/myeongri_interpret_lora_v0/run_interpret_v5_wording_sweep_s100"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--compare-json", type=Path, default=DEFAULT_COMPARE)
    ap.add_argument("--v5-eval-json", type=Path, default=DEFAULT_V5_EVAL)
    ap.add_argument("--v4-eval-json", type=Path, default=DEFAULT_V4_EVAL)
    ap.add_argument("--v5-closure-json", type=Path, default=DEFAULT_V5_CLOSURE)
    ap.add_argument("--status-json", type=Path, default=DEFAULT_STATUS)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    compare = json.loads(args.compare_json.read_text(encoding="utf-8")) if args.compare_json.is_file() else {}
    v5_eval = json.loads(args.v5_eval_json.read_text(encoding="utf-8")) if args.v5_eval_json.is_file() else {}
    v4_eval = json.loads(args.v4_eval_json.read_text(encoding="utf-8")) if args.v4_eval_json.is_file() else {}
    status = json.loads(args.status_json.read_text(encoding="utf-8")) if args.status_json.is_file() else {}
    v5_closed = args.v5_closure_json.is_file()

    v5_cal_closed = False
    if v5_closed:
        c = json.loads(args.v5_closure_json.read_text(encoding="utf-8"))
        v5_cal_closed = c.get("phase_status") == "closed"

    current_adapter = str(status.get("recommended_operational_adapter") or V4_ADAPTER)
    promotion = status.get("operational_adapter_promotion_v5") or {}
    promotion_active = promotion.get("status") == "active"
    candidate_adapter = V5_ADAPTER
    swap_recommended = promotion_active or (
        v5_cal_closed
        and v5_eval.get("parse_ok_rate") == 1.0
        and (v5_eval.get("envelope_coerced_rate") or 1.0) <= 0.15
    )

    readiness = {
        "schema": "myeongri_interpret_v5_operational_promotion_readiness_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "current_operational_adapter": current_adapter,
        "candidate_adapter": candidate_adapter,
        "swap_recommended": swap_recommended,
        "swap_requires": [
            "commander_ops_signoff_explicit",
            "harness recommended_operational_adapter field update",
            "Track A human gate — not auto from B-track bench",
        ],
        "evidence": {
            "v5_calibration30_closed": v5_cal_closed,
            "v5_locked100_parse_ok_rate": v5_eval.get("parse_ok_rate"),
            "v5_envelope_coerced_rate": v5_eval.get("envelope_coerced_rate"),
            "v4_envelope_coerced_rate": v4_eval.get("envelope_coerced_rate"),
            "cal30_insight_changed_count": compare.get("insight_changed_count"),
            "v5_calibration_gate_pass": compare.get("v5_calibration_gate_pass"),
        },
        "interpretation_ko": (
            "v5 운영 승격(active) 상태 유지; B-track 근거 정합 확인. "
            "Track A·실매매 자동 승격은 별도 human gate 필요."
            if promotion_active
            else (
                "v5는 population coerce·서술 품질에서 v4 대비 개선 신호가 있으나, "
                "운영 어댑터 교체는 별도 ops 승인 전까지 v4 유지."
            )
        ),
        "track_wall": {"track_a_live_auto_merge": False, "auto_swap_operational_adapter": False},
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(readiness, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "swap_recommended": False, "out": str(args.out_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
