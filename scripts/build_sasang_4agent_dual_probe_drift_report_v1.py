#!/usr/bin/env python3
"""Dual-probe drift report vs stored baseline [HYPO]."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CURRENT = ROOT / "reports/sasang_4agent_dual_probe_compare_v1_latest.json"
BASELINE = ROOT / "reports/sasang_4agent_dual_probe_compare_v1_baseline.json"
OUT = ROOT / "reports/sasang_4agent_dual_probe_drift_v1_latest.json"
MDD_DRIFT_MAX = 0.02


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _mdd(doc: dict[str, Any], key: str) -> float:
    block = doc.get(key) if isinstance(doc.get(key), dict) else {}
    return float(block.get("mdd_reduction_abs") or 0.0)


def build(*, seed_baseline: bool = False) -> dict[str, Any]:
    current = _load(CURRENT)
    if current.get("schema") != "sasang_4agent_dual_probe_compare_v1":
        return {
            "schema": "sasang_4agent_dual_probe_drift_v1",
            "generated_at_utc": _utc(),
            "drift_ok": False,
            "drift_status": "missing_current_compare",
        }

    baseline = _load(BASELINE)
    if seed_baseline or not baseline or baseline.get("schema") != "sasang_4agent_dual_probe_compare_v1":
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(CURRENT, BASELINE)
        return {
            "schema": "sasang_4agent_dual_probe_drift_v1",
            "generated_at_utc": _utc(),
            "lane": "track_b_hypo",
            "non_gating": True,
            "drift_status": "baseline_seeded",
            "drift_ok": True,
            "baseline_path": str(BASELINE).replace("\\", "/"),
            "current_path": str(CURRENT).replace("\\", "/"),
            "reproduce": "py scripts/build_sasang_4agent_dual_probe_drift_report_v1.py",
        }

    drifts = {
        "real_slice_mdd_delta": round(_mdd(current, "real_slice") - _mdd(baseline, "real_slice"), 6),
        "timeseries_mdd_delta": round(_mdd(current, "timeseries_kospi") - _mdd(baseline, "timeseries_kospi"), 6),
        "cross_probe_delta_shift": round(
            float((current.get("delta") or {}).get("mdd_reduction_abs_timeseries_minus_real_slice") or 0.0)
            - float((baseline.get("delta") or {}).get("mdd_reduction_abs_timeseries_minus_real_slice") or 0.0),
            6,
        ),
    }
    max_abs = max(abs(drifts["real_slice_mdd_delta"]), abs(drifts["timeseries_mdd_delta"]))
    drift_ok = max_abs <= MDD_DRIFT_MAX
    return {
        "schema": "sasang_4agent_dual_probe_drift_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "drift_status": "within_band" if drift_ok else "drift_alert",
        "drift_ok": drift_ok,
        "thresholds": {"mdd_abs_max": MDD_DRIFT_MAX},
        "drifts": drifts,
        "max_abs_mdd_drift": round(max_abs, 6),
        "baseline_generated_at_utc": baseline.get("generated_at_utc"),
        "current_generated_at_utc": current.get("generated_at_utc"),
        "reproduce": "py scripts/build_sasang_4agent_dual_probe_drift_report_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed-baseline", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build(seed_baseline=args.seed_baseline)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("drift_ok"), "drift_status": doc.get("drift_status")}))
    return 0 if doc.get("drift_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
