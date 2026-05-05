#!/usr/bin/env python3
"""Run walk-forward style size-lane eval for compression bridge."""

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
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "compression_bridge_size_walkforward_eval_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> tuple[int, str, str]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    return cp.returncode, cp.stdout, cp.stderr


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _f(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _policy_from_ensemble(path: Path) -> dict[str, float]:
    if not path.is_file():
        return {"size_floor": 0.1, "size_cap": 1.0, "neutral_size_scalar": 0.0}
    cfg = _load_json(path)
    rules = cfg.get("rules") if isinstance(cfg.get("rules"), dict) else {}
    floor = max(0.0, min(1.0, _f(rules.get("compression_bridge_size_floor")) or 0.1))
    cap = max(floor, min(1.0, _f(rules.get("compression_bridge_size_cap")) or 1.0))
    neutral = max(0.0, min(1.0, _f(rules.get("compression_bridge_neutral_size_scalar")) or 0.0))
    return {"size_floor": floor, "size_cap": cap, "neutral_size_scalar": neutral}


def _windows_from_range(start: int, stop: int, step: int) -> list[int]:
    vals = list(range(max(1, start), max(start, stop) + 1, max(1, step)))
    return [v for v in vals if v > 0]


def main() -> int:
    ap = argparse.ArgumentParser(description="Walk-forward style eval for compression bridge size lane.")
    ap.add_argument("--start-days", type=int, default=30)
    ap.add_argument("--stop-days", type=int, default=180)
    ap.add_argument("--step-days", type=int, default=30)
    ap.add_argument("--ensemble-config", type=Path, default=DEFAULT_ENSEMBLE)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    windows = _windows_from_range(args.start_days, args.stop_days, args.step_days)
    if not windows:
        print("invalid walk-forward range", file=sys.stderr)
        return 2

    size_policy = _policy_from_ensemble(args.ensemble_config)
    rows: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="bridge_walkforward_eval_") as td:
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
                rows.append({"window_days": w, "status": "error", "error": (err or out).strip()[:800]})
                continue
            probe = _load_json(out_path)
            comp = probe.get("comparison") if isinstance(probe.get("comparison"), dict) else {}
            legs = probe.get("legs") if isinstance(probe.get("legs"), dict) else {}
            on = legs.get("bridge_on") if isinstance(legs.get("bridge_on"), dict) else {}
            off = legs.get("bridge_off") if isinstance(legs.get("bridge_off"), dict) else {}
            on_size = on.get("size_policy") if isinstance(on.get("size_policy"), dict) else {}
            off_size = off.get("size_policy") if isinstance(off.get("size_policy"), dict) else {}
            rows.append(
                {
                    "window_days": w,
                    "status": "ok",
                    "prediction_direction_on": on.get("prediction_direction"),
                    "prediction_direction_off": off.get("prediction_direction"),
                    "delta_price_directional_hit_rate": comp.get("delta_price_directional_hit_rate"),
                    "delta_size_scalar": comp.get("delta_size_scalar"),
                    "delta_size_weighted_payoff_mean": comp.get("delta_size_weighted_payoff_mean"),
                    "size_scalar_on": on_size.get("size_scalar"),
                    "size_scalar_off": off_size.get("size_scalar"),
                }
            )

    ok_rows = [r for r in rows if r.get("status") == "ok"]
    direction_changed_rows = sum(
        1 for r in ok_rows if r.get("prediction_direction_on") != r.get("prediction_direction_off")
    )
    min_hit_delta = min((_f(r.get("delta_price_directional_hit_rate")) for r in ok_rows), default=0.0)
    min_size_delta = min((_f(r.get("delta_size_weighted_payoff_mean")) for r in ok_rows), default=0.0)
    mean_size_delta = (
        sum(_f(r.get("delta_size_weighted_payoff_mean")) for r in ok_rows) / len(ok_rows) if ok_rows else 0.0
    )
    pass_walkforward = bool(ok_rows) and direction_changed_rows == 0 and min_hit_delta >= 0.0 and min_size_delta >= 0.0

    out_doc = {
        "schema": "compression_bridge_size_walkforward_eval_v1",
        "generated_at_utc": _utc_now(),
        "inputs": {
            "start_days": args.start_days,
            "stop_days": args.stop_days,
            "step_days": args.step_days,
            "ensemble_config_path": str(args.ensemble_config.resolve()),
            "size_policy": size_policy,
        },
        "windows": windows,
        "rows": rows,
        "summary": {
            "ok_rows": len(ok_rows),
            "direction_changed_rows": direction_changed_rows,
            "min_delta_price_directional_hit_rate": round(min_hit_delta, 8),
            "min_delta_size_weighted_payoff_mean": round(min_size_delta, 8),
            "mean_delta_size_weighted_payoff_mean": round(mean_size_delta, 8),
        },
        "decision": "PASS_WALKFORWARD_SIZE_LANE" if pass_walkforward else "HOLD_WALKFORWARD_SIZE_LANE",
        "fact_safe_note": "Walk-forward gate is size-only and keeps direction lane isolated.",
        "out_of_scope": "No automatic Track A/B promotion and no live trigger.",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

