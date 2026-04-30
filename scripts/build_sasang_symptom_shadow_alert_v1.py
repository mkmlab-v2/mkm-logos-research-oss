#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVAL_JSON = ROOT / "docs" / "final" / "artifacts" / "sasang_symptom_transition_eval_latest.json"
DEFAULT_LEAKAGE_JSON = ROOT / "docs" / "final" / "artifacts" / "sasang_symptom_transition_leakage_audit_latest.json"
DEFAULT_OUT_JSON = ROOT / "docs" / "final" / "artifacts" / "sasang_symptom_transition_shadow_alert_latest.json"


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build shadow alert status from transition eval + leakage audit.")
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL_JSON)
    ap.add_argument("--leakage-json", type=Path, default=DEFAULT_LEAKAGE_JSON)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    args = ap.parse_args()

    ev = _load_json(args.eval_json)
    lk = _load_json(args.leakage_json)
    metrics = ev.get("metrics") if isinstance(ev.get("metrics"), dict) else {}
    label_mode_summary = ev.get("label_mode_summary") if isinstance(ev.get("label_mode_summary"), dict) else {}
    primary_label_mode = str(label_mode_summary.get("primary_label_mode", "unknown"))
    calibration = ev.get("calibration") if isinstance(ev.get("calibration"), dict) else {}
    cal_iso = (
        calibration.get("isotonic_lite_after_temperature")
        if isinstance(calibration.get("isotonic_lite_after_temperature"), dict)
        else {}
    )
    n_usable = int(ev.get("n_usable", 0))
    coverage = float(ev.get("coverage_ratio", 0.0))
    brier_raw = float(metrics.get("brier_worsening", 1.0))
    ece_raw = float(metrics.get("ece_worsening", 1.0))
    brier = float(cal_iso.get("brier_worsening", brier_raw))
    ece = float(cal_iso.get("ece_worsening", ece_raw))
    leakage_status = str(lk.get("status", "fail")).lower()
    leakage_ratio = float(lk.get("leakage_ratio", 1.0))
    positive_count = int(metrics.get("positive_label_count", 0))
    negative_count = int(metrics.get("negative_label_count", 0))

    level = "INFO"
    action = "hold_shadow"
    reasons = []
    if leakage_status != "pass" or leakage_ratio > 0.0:
        level = "CRITICAL"
        action = "block"
        reasons.append("temporal_leakage_detected")
    elif positive_count < 5 or negative_count < 5:
        level = "WATCH"
        action = "shadow_collect_balanced_labels"
        reasons.append("class_imbalance_or_single_class_labels")
    elif n_usable < 30 or coverage < 0.95:
        level = "WATCH"
        action = "keep_shadow_collect_more_data"
        reasons.append("insufficient_sample_or_coverage")
    elif brier <= 0.20 and ece <= 0.12:
        level = "GO_SHADOW"
        action = "candidate_for_btrack_shadow_promotion"
        reasons.append("quality_gate_pass")
    else:
        level = "WATCH"
        action = "shadow_tune_and_retest"
        reasons.append("quality_gate_not_met")

    out = {
        "schema_version": "sasang_symptom_transition_shadow_alert_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "label_mode": primary_label_mode,
        "track_wall": {
            "track_b_only": True,
            "a_track_autobind_forbidden": True,
            "human_review_required_for_any_live_promotion": True,
        },
        "shadow_alert": {
            "level": level,
            "recommended_action": action,
            "reasons": reasons,
        },
        "inputs": {
            "eval_json": str(args.eval_json),
            "leakage_json": str(args.leakage_json),
        },
        "checks": {
            "n_usable": n_usable,
            "coverage_ratio": coverage,
            "primary_label_mode": primary_label_mode,
            "label_mode_counts": label_mode_summary.get("counts", {}),
            "brier_worsening_raw": brier_raw,
            "ece_worsening_raw": ece_raw,
            "brier_worsening": brier,
            "ece_worsening": ece,
            "leakage_status": leakage_status,
            "leakage_ratio": leakage_ratio,
            "positive_label_count": positive_count,
            "negative_label_count": negative_count,
        },
        "note": "Probabilistic trajectory warning system only; deterministic price prediction forbidden.",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
