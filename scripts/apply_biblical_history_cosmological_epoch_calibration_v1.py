#!/usr/bin/env python3
"""Apply [HYPO] cosmological epoch calibration matrix to a chronology sidecar (B-track smoke)."""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CALIBRATION = ROOT / "tests/fixtures/biblical_history_cosmological_epoch_calibration_v1.json"
DEFAULT_BC1 = ROOT / "docs/final/artifacts/biblical_history_h_bc1_bronze_collapse_chronology_sidecar_v1.json"
DEFAULT_OUT = ROOT / "reports/biblical_history_cosmological_calibration_smoke_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _node_mids(sidecar: dict[str, Any], era: str) -> list[int]:
    key = "date_ce_mid" if era == "ce" else "date_bce_mid"
    out: list[int] = []
    for n in sidecar.get("nodes") or []:
        if isinstance(n, dict) and isinstance(n.get(key), int):
            out.append(int(n[key]))
    return out


def _apply_calibration(sidecar: dict[str, Any], cal: dict[str, Any], *, era: str) -> dict[str, Any]:
    key = "date_ce_mid" if era == "ce" else "date_bce_mid"
    shift_key = "mid_shift_ce_years" if era == "ce" else "mid_shift_bce_years"
    expand_key = "window_expand_ce_years" if era == "ce" else "window_expand_bce_years"
    window_key = "epoch_window_ce" if era == "ce" else "epoch_window_bce"

    span_scale = float(cal.get("span_scale", 1.0))
    mid_shift = int(cal.get(shift_key, cal.get("mid_shift_bce_years", 0)) or 0)
    window_expand = int(cal.get(expand_key, cal.get("window_expand_bce_years", 0)) or 0)

    out = copy.deepcopy(sidecar)
    mids = _node_mids(out, era)
    if not mids:
        return out
    centroid = sum(mids) / len(mids)
    for node in out.get("nodes") or []:
        if not isinstance(node, dict) or not isinstance(node.get(key), int):
            continue
        old = int(node[key])
        node[key] = int(round(centroid + (old - centroid) * span_scale + mid_shift))

    window = out.get(window_key)
    if isinstance(window, dict) and window_expand:
        window["start"] = int(window.get("start", 0)) - window_expand
        window["end"] = int(window.get("end", 0)) + window_expand

    out["cosmological_calibration_applied"] = {
        "era": era,
        "span_scale": span_scale,
        "mid_shift_years": mid_shift,
        "window_expand_years": window_expand,
        "model_family": "linear_epoch_rescale_stub_v1",
        "hypothesis_tier": "[HYPO]",
    }
    return out


def _run_permutation(sidecar_path: Path, out_path: Path, *, era: str | None = None) -> int:
    cmd = [
        sys.executable,
        str(ROOT / "scripts/eval_biblical_history_h_bc1_epoch_permutation_v1.py"),
        "--sidecar-json",
        str(sidecar_path),
        "--output-json",
        str(out_path),
    ]
    if era:
        cmd.extend(["--era", era])
    p = subprocess.run(cmd, cwd=str(ROOT), check=False)
    return int(p.returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description="Cosmological epoch calibration smoke (B-track).")
    ap.add_argument("--calibration-json", type=Path, default=DEFAULT_CALIBRATION)
    ap.add_argument("--sidecar-json", type=Path, default=DEFAULT_BC1)
    ap.add_argument("--hypothesis-id", default="H-BC1")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--write-calibrated-sidecar", type=Path, default=None)
    args = ap.parse_args()

    cal_doc = _load(args.calibration_json)
    sidecar = _load(args.sidecar_json)
    hyp_id = str(args.hypothesis_id)
    cal = (cal_doc.get("calibrations") or {}).get(hyp_id)
    if not isinstance(cal, dict):
        raise SystemExit(f"missing calibration entry for {hyp_id}")

    baseline_perm_out = ROOT / "reports/tmp_cosmo_cal_baseline_perm_latest.json"
    calibrated_sidecar_path = args.write_calibrated_sidecar or (
        ROOT / f"reports/tmp_{hyp_id.lower()}_cosmo_calibrated_sidecar_latest.json"
    )
    calibrated_perm_out = ROOT / "reports/tmp_cosmo_cal_adjusted_perm_latest.json"

    calibrated_sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_sidecar_copy = ROOT / "reports/tmp_cosmo_cal_baseline_sidecar_latest.json"
    baseline_sidecar_copy.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rc_base = _run_permutation(baseline_sidecar_copy, baseline_perm_out, era="bce")
    if rc_base != 0:
        raise SystemExit(f"baseline permutation failed: exit {rc_base}")

    calibrated = _apply_calibration(sidecar, cal, era="bce")
    calibrated_sidecar_path.write_text(json.dumps(calibrated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rc_adj = _run_permutation(calibrated_sidecar_path, calibrated_perm_out, era="bce")
    if rc_adj != 0:
        raise SystemExit(f"calibrated permutation failed: exit {rc_adj}")

    baseline_perm = _load(baseline_perm_out)
    adjusted_perm = _load(calibrated_perm_out)
    p_base = (baseline_perm.get("permutation_p_values") or {}).get("p_in_window_ge_observed")
    p_adj = (adjusted_perm.get("permutation_p_values") or {}).get("p_in_window_ge_observed")

    report = {
        "schema": "biblical_history_cosmological_calibration_smoke_v1",
        "generated_at_utc": _utc_now(),
        "research_rail": "B",
        "hypothesis_tier": "[HYPO]",
        "gating_status": "NON_GATING",
        "hypothesis_id": hyp_id,
        "inputs": {
            "calibration_json": str(args.calibration_json),
            "sidecar_json": str(args.sidecar_json),
            "calibrated_sidecar_json": str(calibrated_sidecar_path),
        },
        "baseline_permutation": str(baseline_perm_out),
        "adjusted_permutation": str(calibrated_perm_out),
        "delta": {
            "p_in_window_ge_observed_baseline": p_base,
            "p_in_window_ge_observed_adjusted": p_adj,
            "p_delta_adjusted_minus_baseline": None
            if p_base is None or p_adj is None
            else round(float(p_adj) - float(p_base), 6),
        },
        "interpretation": {
            "status": "research_only_not_promotion_proof",
            "note": "Linear epoch rescale stub; not nonlinear spacetime physics.",
        },
        "track_a_promotion": "blocked",
        "live_trading_trigger": "forbidden",
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.output_json), "hypothesis_id": hyp_id}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
