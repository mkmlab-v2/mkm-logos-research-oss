#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_CAL = ART / "myeongni_stage2_calibration_report_latest.json"
DEFAULT_BASE = ART / "mkm_myeongni_response_v2_stage2_baseline_latest.json"
DEFAULT_NEW = ART / "mkm_myeongni_response_v2_stage2_latest.json"
DEFAULT_OUT = ART / "myeongni_stage2_apply_diff_report_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _decision(doc: dict[str, Any]) -> str:
    fa = doc.get("final_action") if isinstance(doc.get("final_action"), dict) else {}
    return str(fa.get("decision") or "UNKNOWN").upper()


def main() -> int:
    ap = argparse.ArgumentParser(description="Build before/after diff report for myeongni stage2 threshold apply.")
    ap.add_argument("--calibration-json", type=Path, default=DEFAULT_CAL)
    ap.add_argument("--baseline-json", type=Path, default=DEFAULT_BASE)
    ap.add_argument("--applied-json", type=Path, default=DEFAULT_NEW)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    cal_path = args.calibration_json if args.calibration_json.is_absolute() else ROOT / args.calibration_json
    base_path = args.baseline_json if args.baseline_json.is_absolute() else ROOT / args.baseline_json
    new_path = args.applied_json if args.applied_json.is_absolute() else ROOT / args.applied_json

    cal = _read_json(cal_path)
    base = _read_json(base_path)
    new = _read_json(new_path)
    best = cal.get("best_thresholds") if isinstance(cal.get("best_thresholds"), dict) else {}

    base_dec = _decision(base)
    new_dec = _decision(new)
    changed = base_dec != new_dec

    rows = cal.get("rows") if isinstance(cal.get("rows"), list) else []
    sample_transition = {
        "total": len(rows),
        "watch_to_reduce": sum(1 for r in rows if str(r.get("label_current")) == "WATCH" and str(r.get("label_recalibrated")) == "REDUCE"),
        "watch_to_hold": sum(1 for r in rows if str(r.get("label_current")) == "WATCH" and str(r.get("label_recalibrated")) == "HOLD"),
        "reduce_to_watch": sum(1 for r in rows if str(r.get("label_current")) == "REDUCE" and str(r.get("label_recalibrated")) == "WATCH"),
        "unchanged": sum(1 for r in rows if str(r.get("label_current")) == str(r.get("label_recalibrated"))),
    }

    out = {
        "schema": "myeongni_stage2_apply_diff_report_v1",
        "generated_at_utc": _now(),
        "inputs": {
            "calibration_json": str(cal_path.resolve()),
            "baseline_json": str(base_path.resolve()),
            "applied_json": str(new_path.resolve()),
        },
        "thresholds_applied": {
            "hold_confidence_cut": best.get("hold_confidence_cut"),
            "reduce_direction_cut": best.get("reduce_direction_cut"),
            "reduce_confidence_cut": best.get("reduce_confidence_cut"),
        },
        "single_run_decision_diff": {
            "baseline_decision": base_dec,
            "applied_decision": new_dec,
            "changed": changed,
        },
        "sample_transition_from_calibration": sample_transition,
    }

    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "changed": changed}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
