#!/usr/bin/env python3
"""Sweep compression-bridge adjustment knobs and compare ON/OFF impact reports.

Research-only helper around build_compression_bridge_impact_probe_v1.py.
"""

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
DEFAULT_BASE_CFG = ROOT / "docs" / "final" / "artifacts" / "btrack_lens_ensemble_v1.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "compression_bridge_adjustment_sweep_latest.json"
PROBE_SCRIPT = ROOT / "scripts" / "build_compression_bridge_impact_probe_v1.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> tuple[int, str, str]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    return cp.returncode, cp.stdout, cp.stderr


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_float(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _set_rules(base_cfg: dict[str, Any], *, signal_scale: float, pos_cap: float) -> dict[str, Any]:
    cfg = json.loads(json.dumps(base_cfg, ensure_ascii=False))
    rules = cfg.get("rules")
    if not isinstance(rules, dict):
        rules = {}
        cfg["rules"] = rules
    rules["compression_bridge_signal_scale"] = float(signal_scale)
    rules["compression_bridge_positive_signal_cap"] = float(pos_cap)
    rules.setdefault("compression_bridge_negative_signal_cap", 0.02)
    rules.setdefault("compression_bridge_margin_shrink_scale", 0.2)
    rules.setdefault("compression_bridge_neutral_relief_scale", 0.4)
    rules.setdefault("compression_bridge_negative_penalty_scale", 0.5)
    return cfg


def main() -> int:
    ap = argparse.ArgumentParser(description="Sweep compression bridge adjustment knobs.")
    ap.add_argument("--base-ensemble-config", type=Path, default=DEFAULT_BASE_CFG)
    ap.add_argument("--recent-trading-days", type=int, default=30)
    ap.add_argument("--signal-scales", type=str, default="0.0,0.5,1.0,2.0,3.0")
    ap.add_argument("--positive-caps", type=str, default="0.01,0.03,0.05")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.base_ensemble_config.is_file():
        print(f"missing base ensemble config: {args.base_ensemble_config}", file=sys.stderr)
        return 1
    base_cfg = _load_json(args.base_ensemble_config)

    try:
        scales = [float(s.strip()) for s in args.signal_scales.split(",") if s.strip()]
        caps = [float(s.strip()) for s in args.positive_caps.split(",") if s.strip()]
    except ValueError as exc:
        print(f"invalid float in sweep args: {exc}", file=sys.stderr)
        return 2
    if not scales or not caps:
        print("empty sweep grid", file=sys.stderr)
        return 2

    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="bridge_adj_sweep_") as td:
        tdp = Path(td)
        for s in scales:
            for c in caps:
                cfg = _set_rules(base_cfg, signal_scale=s, pos_cap=c)
                cfg_path = tdp / f"cfg_s{s}_c{c}.json"
                probe_path = tdp / f"probe_s{s}_c{c}.json"
                cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

                rc, out, err = _run(
                    [
                        sys.executable,
                        str(PROBE_SCRIPT),
                        "--ensemble-config",
                        str(cfg_path),
                        "--recent-trading-days",
                        str(max(1, int(args.recent_trading_days))),
                        "--output",
                        str(probe_path),
                    ]
                )
                if rc != 0:
                    rows.append(
                        {
                            "signal_scale": s,
                            "positive_signal_cap": c,
                            "status": "error",
                            "error": (err or out).strip()[:600],
                        }
                    )
                    continue
                probe = _load_json(probe_path)
                comp = probe.get("comparison") if isinstance(probe.get("comparison"), dict) else {}
                leg_on = (probe.get("legs") or {}).get("bridge_on") if isinstance(probe.get("legs"), dict) else {}
                leg_off = (probe.get("legs") or {}).get("bridge_off") if isinstance(probe.get("legs"), dict) else {}
                rows.append(
                    {
                        "signal_scale": s,
                        "positive_signal_cap": c,
                        "status": "ok",
                        "decision": probe.get("decision"),
                        "prediction_changed": comp.get("prediction_changed"),
                        "delta_weighted_score": comp.get("delta_weighted_score"),
                        "delta_price_directional_hit_rate": comp.get("delta_price_directional_hit_rate"),
                        "on_prediction_direction": (leg_on or {}).get("prediction_direction"),
                        "on_prediction_confidence": (leg_on or {}).get("prediction_confidence"),
                        "off_prediction_direction": (leg_off or {}).get("prediction_direction"),
                        "off_prediction_confidence": (leg_off or {}).get("prediction_confidence"),
                    }
                )

    ok_rows = [r for r in rows if r.get("status") == "ok"]
    best = None
    if ok_rows:
        best = sorted(
            ok_rows,
            key=lambda r: (
                _safe_float(r.get("delta_price_directional_hit_rate")) or 0.0,
                abs(_safe_float(r.get("delta_weighted_score")) or 0.0),
            ),
            reverse=True,
        )[0]

    out = {
        "schema": "compression_bridge_adjustment_sweep_v1",
        "generated_at_utc": _utc_now(),
        "inputs": {
            "base_ensemble_config": str(args.base_ensemble_config.resolve()),
            "recent_trading_days": max(1, int(args.recent_trading_days)),
            "signal_scales": scales,
            "positive_signal_caps": caps,
        },
        "rows": rows,
        "best_candidate": best,
        "fact_safe_note": "Satisfying weighted-score deltas does not prove durable hit-rate uplift. "
        "Use walk-forward / fixed holdout before promotion claims.",
        "out_of_scope": "No live trading trigger; no automatic promotion.",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

