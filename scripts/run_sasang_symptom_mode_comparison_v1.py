#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
EVAL_JSON = ROOT / "docs" / "final" / "artifacts" / "sasang_symptom_transition_eval_latest.json"
ALERT_JSON = ROOT / "docs" / "final" / "artifacts" / "sasang_symptom_transition_shadow_alert_latest.json"
OUT_JSON = ROOT / "docs" / "final" / "artifacts" / "sasang_symptom_transition_mode_comparison_latest.json"


def _run(cmd: list[str]) -> int:
    print("RUN:", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(ROOT))
    return int(proc.returncode)


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _snapshot(label: str) -> Dict[str, Any]:
    ev = _read_json(EVAL_JSON)
    al = _read_json(ALERT_JSON)
    metrics = ev.get("metrics") if isinstance(ev.get("metrics"), dict) else {}
    cal = ev.get("calibration") if isinstance(ev.get("calibration"), dict) else {}
    cal_iso = cal.get("isotonic_lite_after_temperature") if isinstance(cal.get("isotonic_lite_after_temperature"), dict) else {}
    return {
        "mode": label,
        "label_mode": al.get("label_mode"),
        "alert_level": ((al.get("shadow_alert") or {}).get("level") if isinstance(al.get("shadow_alert"), dict) else None),
        "recommended_action": (
            (al.get("shadow_alert") or {}).get("recommended_action")
            if isinstance(al.get("shadow_alert"), dict)
            else None
        ),
        "n_usable": ev.get("n_usable"),
        "coverage_ratio": ev.get("coverage_ratio"),
        "positive_label_count": metrics.get("positive_label_count"),
        "negative_label_count": metrics.get("negative_label_count"),
        "brier_raw": metrics.get("brier_worsening"),
        "ece_raw": metrics.get("ece_worsening"),
        "brier_calibrated": cal_iso.get("brier_worsening"),
        "ece_calibrated": cal_iso.get("ece_worsening"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Run natural vs balanced mode comparison for sasang symptom transition chain.")
    ap.add_argument("--horizon-days", type=int, default=3)
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    args = ap.parse_args()

    py = sys.executable
    natural_cmd = [py, "scripts/run_sasang_symptom_shadow_chain_v1.py", "--horizon-days", str(max(1, int(args.horizon_days)))]
    balanced_cmd = natural_cmd + ["--inject-balanced-labels"]

    code = _run(natural_cmd)
    if code != 0:
        return code
    natural = _snapshot("natural_horizon")

    code = _run(balanced_cmd)
    if code != 0:
        return code
    balanced = _snapshot("balanced_synthetic")

    out = {
        "schema_version": "sasang_symptom_transition_mode_comparison_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "track_wall": {"track_b_only": True, "a_track_autobind_forbidden": True},
        "runs": {
            "natural_horizon": natural,
            "balanced_synthetic": balanced,
        },
        "summary": {
            "natural_alert_level": natural.get("alert_level"),
            "balanced_alert_level": balanced.get("alert_level"),
            "natural_positive_label_count": natural.get("positive_label_count"),
            "balanced_positive_label_count": balanced.get("positive_label_count"),
        },
        "note": "Comparison is for B-track shadow diagnostics only; no deterministic price prediction use.",
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
