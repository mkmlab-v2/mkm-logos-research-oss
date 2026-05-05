#!/usr/bin/env python3
"""Directional-impact sweep for compression bridge adjustments.

Goal: find parameter regions where bridge ON/OFF changes prediction direction
and/or hit-rate, not just confidence/weighted score.
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
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "compression_bridge_directional_impact_sweep_latest.json"
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


def _set_rules(
    base_cfg: dict[str, Any],
    *,
    signal_scale: float,
    negative_cap: float,
    tie_break_margin: float,
) -> dict[str, Any]:
    cfg = json.loads(json.dumps(base_cfg, ensure_ascii=False))
    rules = cfg.get("rules")
    if not isinstance(rules, dict):
        rules = {}
        cfg["rules"] = rules
    rules["compression_bridge_signal_scale"] = float(signal_scale)
    rules["compression_bridge_negative_signal_cap"] = float(negative_cap)
    rules["tie_break_min_margin"] = float(tie_break_margin)
    # keep positive path conservative; this sweep focuses on direction boundary.
    rules.setdefault("compression_bridge_positive_signal_cap", 0.03)
    rules.setdefault("compression_bridge_margin_shrink_scale", 0.2)
    rules.setdefault("compression_bridge_neutral_relief_scale", 0.4)
    rules.setdefault("compression_bridge_negative_penalty_scale", 0.5)
    return cfg


def main() -> int:
    ap = argparse.ArgumentParser(description="Sweep directional impact of compression bridge knobs.")
    ap.add_argument("--base-ensemble-config", type=Path, default=DEFAULT_BASE_CFG)
    ap.add_argument("--recent-trading-days", type=int, default=30)
    ap.add_argument("--signal-scales", type=str, default="0,1,5,10,20")
    ap.add_argument("--negative-caps", type=str, default="0.02,0.05,0.1,0.2")
    ap.add_argument("--tie-break-margins", type=str, default="0.03,0.08,0.12")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.base_ensemble_config.is_file():
        print(f"missing base ensemble config: {args.base_ensemble_config}", file=sys.stderr)
        return 1
    base_cfg = _load_json(args.base_ensemble_config)

    try:
        scales = [float(s.strip()) for s in args.signal_scales.split(",") if s.strip()]
        neg_caps = [float(s.strip()) for s in args.negative_caps.split(",") if s.strip()]
        margins = [float(s.strip()) for s in args.tie_break_margins.split(",") if s.strip()]
    except ValueError as exc:
        print(f"invalid float in sweep args: {exc}", file=sys.stderr)
        return 2
    if not scales or not neg_caps or not margins:
        print("empty sweep grid", file=sys.stderr)
        return 2

    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="bridge_dir_sweep_") as td:
        tdp = Path(td)
        for scale in scales:
            for ncap in neg_caps:
                for margin in margins:
                    cfg = _set_rules(base_cfg, signal_scale=scale, negative_cap=ncap, tie_break_margin=margin)
                    cfg_path = tdp / f"cfg_s{scale}_n{ncap}_m{margin}.json"
                    probe_path = tdp / f"probe_s{scale}_n{ncap}_m{margin}.json"
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
                                "signal_scale": scale,
                                "negative_signal_cap": ncap,
                                "tie_break_min_margin": margin,
                                "status": "error",
                                "error": (err or out).strip()[:600],
                            }
                        )
                        continue

                    probe = _load_json(probe_path)
                    legs = probe.get("legs") if isinstance(probe.get("legs"), dict) else {}
                    on = legs.get("bridge_on") if isinstance(legs.get("bridge_on"), dict) else {}
                    off = legs.get("bridge_off") if isinstance(legs.get("bridge_off"), dict) else {}
                    comp = probe.get("comparison") if isinstance(probe.get("comparison"), dict) else {}
                    row = {
                        "signal_scale": scale,
                        "negative_signal_cap": ncap,
                        "tie_break_min_margin": margin,
                        "status": "ok",
                        "decision": probe.get("decision"),
                        "prediction_changed": comp.get("prediction_changed"),
                        "delta_weighted_score": comp.get("delta_weighted_score"),
                        "delta_price_directional_hit_rate": comp.get("delta_price_directional_hit_rate"),
                        "on_prediction_direction": on.get("prediction_direction"),
                        "off_prediction_direction": off.get("prediction_direction"),
                        "on_prediction_confidence": on.get("prediction_confidence"),
                        "off_prediction_confidence": off.get("prediction_confidence"),
                    }
                    rows.append(row)

    ok_rows = [r for r in rows if r.get("status") == "ok"]
    directional_rows = [r for r in ok_rows if r.get("on_prediction_direction") != r.get("off_prediction_direction")]
    best_hit = None
    if ok_rows:
        best_hit = sorted(
            ok_rows,
            key=lambda r: (
                _safe_float(r.get("delta_price_directional_hit_rate")) or 0.0,
                1.0 if bool(r.get("prediction_changed")) else 0.0,
                abs(_safe_float(r.get("delta_weighted_score")) or 0.0),
            ),
            reverse=True,
        )[0]

    out = {
        "schema": "compression_bridge_directional_impact_sweep_v1",
        "generated_at_utc": _utc_now(),
        "inputs": {
            "base_ensemble_config": str(args.base_ensemble_config.resolve()),
            "recent_trading_days": max(1, int(args.recent_trading_days)),
            "signal_scales": scales,
            "negative_signal_caps": neg_caps,
            "tie_break_margins": margins,
        },
        "rows": rows,
        "summary": {
            "total_rows": len(rows),
            "ok_rows": len(ok_rows),
            "direction_changed_rows": len(directional_rows),
        },
        "best_hit_candidate": best_hit,
        "fact_safe_note": "Direction change alone is not sufficient for promotion. Require fixed holdout / walk-forward uplift.",
        "out_of_scope": "No live trigger and no automatic Track promotion.",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

