#!/usr/bin/env python3
"""Run fixed-window holdout eval for compression bridge size-only impact."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROBE_SCRIPT = ROOT / "scripts" / "build_compression_bridge_impact_probe_v1.py"
DEFAULT_ENSEMBLE = ROOT / "docs" / "final" / "artifacts" / "btrack_lens_ensemble_v1.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "compression_bridge_size_holdout_eval_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> tuple[int, str, str]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    return cp.returncode, cp.stdout, cp.stderr


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _f(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _policy_from_ensemble(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"mode": "confidence_only_scalar_v1", "size_floor": 0.1, "size_cap": 1.0, "neutral_size_scalar": 0.0}
    cfg = _load_json(path)
    rules = cfg.get("rules") if isinstance(cfg.get("rules"), dict) else {}
    floor = max(0.0, min(1.0, _f(rules.get("compression_bridge_size_floor")) or 0.1))
    cap = max(floor, min(1.0, _f(rules.get("compression_bridge_size_cap")) or 1.0))
    neutral_scalar = max(0.0, min(1.0, _f(rules.get("compression_bridge_neutral_size_scalar")) or 0.0))
    return {
        "mode": str(rules.get("compression_bridge_size_mode") or "confidence_only_scalar_v1"),
        "size_floor": floor,
        "size_cap": cap,
        "neutral_size_scalar": neutral_scalar,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Fixed-window holdout eval for bridge size-only impact.")
    ap.add_argument("--windows", type=str, default="30,60,120")
    ap.add_argument("--ensemble-config", type=Path, default=DEFAULT_ENSEMBLE)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    try:
        windows = [int(x.strip()) for x in args.windows.split(",") if x.strip()]
    except ValueError as exc:
        print(f"invalid windows: {exc}", file=sys.stderr)
        return 2
    windows = [w for w in windows if w > 0]
    if not windows:
        print("no valid windows", file=sys.stderr)
        return 2
    size_policy = _policy_from_ensemble(args.ensemble_config)

    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="bridge_holdout_eval_") as td:
        tdp = Path(td)
        for w in windows:
            out_path = tdp / f"probe_{w}.json"
            rc, out, err = _run(
                [
                    sys.executable,
                    str(PROBE_SCRIPT),
                    "--recent-trading-days",
                    str(w),
                    "--ensemble-config",
                    str(args.ensemble_config),
                    "--size-floor",
                    str(size_policy["size_floor"]),
                    "--size-cap",
                    str(size_policy["size_cap"]),
                    "--neutral-size-scalar",
                    str(size_policy["neutral_size_scalar"]),
                    "--output",
                    str(out_path),
                ]
            )
            if rc != 0:
                rows.append(
                    {
                        "window_days": w,
                        "status": "error",
                        "error": (err or out).strip()[:800],
                    }
                )
                continue
            p = _load_json(out_path)
            comp = p.get("comparison") if isinstance(p.get("comparison"), dict) else {}
            on = ((p.get("legs") or {}).get("bridge_on") or {}) if isinstance(p.get("legs"), dict) else {}
            off = ((p.get("legs") or {}).get("bridge_off") or {}) if isinstance(p.get("legs"), dict) else {}
            on_size = (on.get("size_policy") or {}) if isinstance(on.get("size_policy"), dict) else {}
            off_size = (off.get("size_policy") or {}) if isinstance(off.get("size_policy"), dict) else {}
            row = {
                "window_days": w,
                "status": "ok",
                "prediction_direction_on": on.get("prediction_direction"),
                "prediction_direction_off": off.get("prediction_direction"),
                "prediction_confidence_on": on.get("prediction_confidence"),
                "prediction_confidence_off": off.get("prediction_confidence"),
                "hit_rate_on": ((on.get("hit_rate_metrics") or {}).get("price_directional_hit_rate")),
                "hit_rate_off": ((off.get("hit_rate_metrics") or {}).get("price_directional_hit_rate")),
                "delta_price_directional_hit_rate": comp.get("delta_price_directional_hit_rate"),
                "size_scalar_on": on_size.get("size_scalar"),
                "size_scalar_off": off_size.get("size_scalar"),
                "delta_size_scalar": comp.get("delta_size_scalar"),
                "payoff_mean_size_weighted_on": on_size.get("payoff_mean_size_weighted"),
                "payoff_mean_size_weighted_off": off_size.get("payoff_mean_size_weighted"),
                "delta_size_weighted_payoff_mean": comp.get("delta_size_weighted_payoff_mean"),
            }
            rows.append(row)

    ok_rows = [r for r in rows if r.get("status") == "ok"]
    dir_changed = [
        r for r in ok_rows if r.get("prediction_direction_on") != r.get("prediction_direction_off")
    ]
    hit_uplift = [r for r in ok_rows if (_f(r.get("delta_price_directional_hit_rate")) or 0.0) > 0.0]
    size_uplift = [r for r in ok_rows if (_f(r.get("delta_size_weighted_payoff_mean")) or 0.0) > 0.0]
    size_degrade = [r for r in ok_rows if (_f(r.get("delta_size_weighted_payoff_mean")) or 0.0) < 0.0]

    out = {
        "schema": "compression_bridge_size_holdout_eval_v1",
        "generated_at_utc": _utc_now(),
        "windows": windows,
        "size_policy": size_policy,
        "ensemble_config_path": str(args.ensemble_config.resolve()),
        "rows": rows,
        "summary": {
            "ok_rows": len(ok_rows),
            "direction_changed_rows": len(dir_changed),
            "hit_rate_uplift_rows": len(hit_uplift),
            "size_weighted_payoff_uplift_rows": len(size_uplift),
            "size_weighted_payoff_degrade_rows": len(size_degrade),
        },
        "decision": (
            "HOLD_SIZE_BRIDGE_TUNING"
            if len(hit_uplift) == 0 and len(size_uplift) == 0
            else "CONTINUE_SIZE_BRIDGE_TUNING"
        ),
        "fact_safe_note": "Holdout eval checks consistency across fixed windows; "
        "promotion still requires broader walk-forward and risk gates.",
        "out_of_scope": "No live trigger and no automatic promotion.",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

