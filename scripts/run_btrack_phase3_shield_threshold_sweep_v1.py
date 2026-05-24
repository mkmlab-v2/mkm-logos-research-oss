#!/usr/bin/env python3
"""Grid sweep: leading_shield_v1 disagree_threshold vs baseline (research_only).

Closes the question: can any threshold make shield beat baseline on headline ALERT_1?
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JOINED_30 = ROOT / "reports/btrack_phase3_leading_sensors_joined_v1_latest.jsonl"
DEFAULT_JOINED_180 = ROOT / "reports/btrack_phase3_leading_sensors_joined_180d_v1_latest.jsonl"
DEFAULT_OUT = ROOT / "reports/btrack_phase3_shield_threshold_sweep_v1_latest.json"
SCHEMA = "btrack_phase3_shield_threshold_sweep_v1"

def _load_lib():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "btrack_phase3_leading_sensors_lib_v1",
        ROOT / "scripts" / "btrack_phase3_leading_sensors_lib_v1.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_lib = _load_lib()
ALERT1 = _lib.ALERT1
hit_metrics = _lib.hit_metrics
read_jsonl = _lib.read_jsonl
rows_baseline = _lib.rows_baseline
rows_for_shield = _lib.rows_for_shield


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def _sweep_window(
    rows: list[dict[str, Any]],
    *,
    window: str,
    thresholds: list[float],
) -> dict[str, Any]:
    base_m = hit_metrics(rows_baseline(rows))
    base_rate = base_m.get("price_directional_hit_rate")
    grid: list[dict[str, Any]] = []
    best: dict[str, Any] | None = None
    for t in thresholds:
        m = hit_metrics(rows_for_shield(rows, threshold=t))
        rate = m.get("price_directional_hit_rate")
        uplift = None
        if isinstance(base_rate, (int, float)) and isinstance(rate, (int, float)):
            uplift = round(float(rate) - float(base_rate), 6)
        row = {
            "disagree_threshold": t,
            "metrics": m,
            "uplift_vs_baseline": uplift,
            "beats_baseline": uplift is not None and uplift > 0,
            "alert_1_pass": m.get("alert_1_pass"),
        }
        grid.append(row)
        if best is None or (rate is not None and (best["metrics"].get("price_directional_hit_rate") or -1) < rate):
            best = row
    beats_any = any(g.get("beats_baseline") for g in grid)
    return {
        "window": window,
        "baseline": base_m,
        "grid": grid,
        "best_shield": best,
        "any_threshold_beats_baseline": beats_any,
        "shield_retirement_recommended": not beats_any,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--joined-30", type=Path, default=DEFAULT_JOINED_30)
    ap.add_argument("--joined-180", type=Path, default=DEFAULT_JOINED_180)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--thresholds",
        default="0.01,0.02,0.03,0.05,0.08,0.10,0.15,0.20,0.30,0.50",
        help="Comma-separated disagree_threshold grid.",
    )
    args = ap.parse_args(argv)

    thresholds = [float(x.strip()) for x in args.thresholds.split(",") if x.strip()]
    windows: list[dict[str, Any]] = []

    if args.joined_30.is_file():
        windows.append(_sweep_window(read_jsonl(args.joined_30), window="30d", thresholds=thresholds))
    if args.joined_180.is_file():
        windows.append(_sweep_window(read_jsonl(args.joined_180), window="180d", thresholds=thresholds))

    if not windows:
        print("No joined JSONL inputs found", file=__import__("sys").stderr)
        return 2

    global_retire = all(w.get("shield_retirement_recommended") for w in windows)

    payload = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "alert_1_threshold": ALERT1,
        "inputs": {
            "joined_30": _rel(args.joined_30) if args.joined_30.is_file() else None,
            "joined_180": _rel(args.joined_180) if args.joined_180.is_file() else None,
        },
        "thresholds": thresholds,
        "windows": windows,
        "verdict": {
            "shield_as_direction_gate": "RETIRED" if global_retire else "HOLD_RESEARCH",
            "track_a_promotion": "NO",
            "auto_promote": False,
            "apply_prod": False,
            "reason_ko": (
                "전 구간에서 shield 최적 threshold도 baseline headline을 넘지 못하면 "
                "선행 센서를 방향 방패로 쓰지 않는다. size/confidence 보조만 허용."
                if global_retire
                else "일부 창에서 threshold가 baseline을 넘음 — 추가 검증 필요(승격 아님)."
            ),
            "next_role": "size_confidence_aux_only",
        },
        "operator_lines": [
            f"- [MKM-SHIELD-SWEEP] retire_shield={global_retire}",
            f"- [MKM-SHIELD-SWEEP] 30d_best={windows[0].get('best_shield', {}).get('disagree_threshold') if windows else 'n/a'}",
        ],
        "rerun": "py scripts/run_btrack_phase3_shield_threshold_sweep_v1.py",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()} retire={global_retire}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
