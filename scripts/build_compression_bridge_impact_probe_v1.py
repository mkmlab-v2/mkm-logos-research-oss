#!/usr/bin/env python3
"""Probe bridge on/off impact for B-track hypothesis + hit-rate chain.

This is a research-only comparator:
- ON: uses current bundle (with compression_bridge_context)
- OFF: uses temporary bundle with compression_bridge_context removed

It runs:
1) generate_btrack_hypothesis_prophecy_v1.py
2) build_btrack_prophecy_score_from_ohlcv.py
3) eval_prophecy_hit_rate_v1.py --run-mode price

Then emits a single comparison artifact.
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
DEFAULT_BUNDLE = ROOT / "docs" / "final" / "artifacts" / "btrack_llm_input_bundle_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "compression_bridge_impact_probe_latest.json"

GEN_SCRIPT = ROOT / "scripts" / "generate_btrack_hypothesis_prophecy_v1.py"
SCORE_SCRIPT = ROOT / "scripts" / "build_btrack_prophecy_score_from_ohlcv.py"
HIT_SCRIPT = ROOT / "scripts" / "eval_prophecy_hit_rate_v1.py"


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


def _size_from_confidence(
    conf: Any,
    *,
    direction: Any,
    floor: float = 0.1,
    cap: float = 1.0,
    neutral_scalar: float = 0.0,
) -> float:
    d = str(direction or "").strip().lower()
    if d == "neutral":
        return round(max(0.0, min(1.0, neutral_scalar)), 6)
    c = _safe_float(conf)
    if c is None:
        return floor
    c = max(0.0, min(1.0, c))
    return round(max(floor, min(cap, c)), 6)


def _directional_payoff(predicted_direction: Any, actual_direction: Any, daily_return: Any) -> float:
    pd = str(predicted_direction or "").strip().lower()
    ad = str(actual_direction or "").strip().lower()
    r = _safe_float(daily_return)
    if r is None:
        return 0.0
    if pd == "neutral":
        return 0.0
    if pd == "bull":
        return r
    if pd == "bear":
        return -r
    return 0.0


def _build_probe_leg(
    *,
    bundle_path: Path,
    hypothesis_out: Path,
    score_out: Path,
    hit_out: Path,
    recent_days: int,
    ensemble_config: Path | None = None,
    size_floor: float = 0.1,
    size_cap: float = 1.0,
    neutral_size_scalar: float = 0.0,
) -> dict[str, Any]:
    gen_cmd = [sys.executable, str(GEN_SCRIPT), "--bundle", str(bundle_path), "--output", str(hypothesis_out)]
    if ensemble_config is not None:
        gen_cmd.extend(["--ensemble-config", str(ensemble_config)])
    rc, out, err = _run(gen_cmd)
    if rc != 0:
        raise RuntimeError(f"hypothesis generation failed: {err or out}")

    rc, out, err = _run(
        [
            sys.executable,
            str(SCORE_SCRIPT),
            "--hypothesis-json",
            str(hypothesis_out),
            "--recent-trading-days",
            str(max(1, int(recent_days))),
            "--output",
            str(score_out),
        ]
    )
    if rc != 0:
        raise RuntimeError(f"score build failed: {err or out}")

    rc, out, err = _run(
        [
            sys.executable,
            str(HIT_SCRIPT),
            "--run-mode",
            "price",
            "--score-json",
            str(score_out),
            "--output",
            str(hit_out),
        ]
    )
    if rc != 0:
        raise RuntimeError(f"hit-rate eval failed: {err or out}")

    hyp = _load_json(hypothesis_out)
    hit = _load_json(hit_out)
    pred = hyp.get("prediction") if isinstance(hyp.get("prediction"), dict) else {}
    runtime = hyp.get("runtime_meta") if isinstance(hyp.get("runtime_meta"), dict) else {}
    bridge = runtime.get("compression_bridge") if isinstance(runtime.get("compression_bridge"), dict) else {}
    confidence_adj = (
        runtime.get("compression_bridge_confidence_adjustment")
        if isinstance(runtime.get("compression_bridge_confidence_adjustment"), dict)
        else {}
    )
    metrics = hit.get("metrics") if isinstance(hit.get("metrics"), dict) else {}
    score_doc = _load_json(score_out)
    score_rows = score_doc.get("rows") if isinstance(score_doc.get("rows"), list) else []
    payoffs = [
        _directional_payoff(
            r.get("predicted_direction"),
            r.get("actual_direction"),
            r.get("daily_return"),
        )
        for r in score_rows
        if isinstance(r, dict)
    ]
    n_rows = len(payoffs)
    payoff_mean = (sum(payoffs) / n_rows) if n_rows else 0.0
    size_scalar = _size_from_confidence(
        pred.get("confidence"),
        direction=pred.get("direction"),
        floor=size_floor,
        cap=size_cap,
        neutral_scalar=neutral_size_scalar,
    )
    size_weighted_payoff_mean = payoff_mean * size_scalar

    return {
        "hypothesis_path": str(hypothesis_out.resolve()),
        "score_path": str(score_out.resolve()),
        "hit_eval_path": str(hit_out.resolve()),
        "prediction_direction": pred.get("direction"),
        "prediction_confidence": pred.get("confidence"),
        "weighted_score": runtime.get("weighted_score"),
        "compression_bridge_available": runtime.get("compression_bridge_available"),
        "compression_bridge_schema": bridge.get("schema"),
        "compression_bridge_confidence_adjustment": confidence_adj,
        "size_policy": {
            "mode": "confidence_only_scalar_v1",
            "size_floor": round(size_floor, 6),
            "size_cap": round(size_cap, 6),
            "neutral_size_scalar": round(neutral_size_scalar, 6),
            "size_scalar": size_scalar,
            "payoff_mean_unscaled": round(payoff_mean, 8),
            "payoff_mean_size_weighted": round(size_weighted_payoff_mean, 8),
            "n_score_rows": n_rows,
        },
        "hit_rate_metrics": {
            "price_directional_hit_rate": metrics.get("price_directional_hit_rate"),
            "n_evaluated": metrics.get("n_evaluated"),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare bridge ON/OFF impact on B-track chain outputs.")
    ap.add_argument("--bundle-json", type=Path, default=DEFAULT_BUNDLE)
    ap.add_argument("--ensemble-config", type=Path, default=None, help="Optional ensemble config for both ON/OFF legs.")
    ap.add_argument("--recent-trading-days", type=int, default=30)
    ap.add_argument("--size-floor", type=float, default=0.1)
    ap.add_argument("--size-cap", type=float, default=1.0)
    ap.add_argument("--neutral-size-scalar", type=float, default=0.0)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.bundle_json.is_file():
        print(f"missing bundle: {args.bundle_json}", file=sys.stderr)
        return 1
    size_floor = max(0.0, min(1.0, float(args.size_floor)))
    size_cap = max(size_floor, min(1.0, float(args.size_cap)))
    neutral_size_scalar = max(0.0, min(1.0, float(args.neutral_size_scalar)))

    bundle_on = _load_json(args.bundle_json)
    if not isinstance(bundle_on, dict):
        print("invalid bundle json object", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="bridge_impact_probe_") as td:
        tdp = Path(td)
        bundle_off_path = tdp / "bundle_off.json"
        hyp_on = tdp / "hyp_on.json"
        hyp_off = tdp / "hyp_off.json"
        score_on = tdp / "score_on.json"
        score_off = tdp / "score_off.json"
        hit_on = tdp / "hit_on.json"
        hit_off = tdp / "hit_off.json"

        # OFF bundle removes compression context + path slots only.
        bundle_off = json.loads(json.dumps(bundle_on, ensure_ascii=False))
        arts = bundle_off.get("artifacts")
        if isinstance(arts, dict):
            arts.pop("compression_bridge_context", None)
        paths = bundle_off.get("artifact_paths")
        if isinstance(paths, dict):
            paths.pop("compression_kpi_summary", None)
            paths.pop("compression_active_report", None)
            paths.pop("compression_decision", None)
        bundle_off_path.write_text(json.dumps(bundle_off, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        leg_on = _build_probe_leg(
            bundle_path=args.bundle_json.resolve(),
            hypothesis_out=hyp_on,
            score_out=score_on,
            hit_out=hit_on,
            recent_days=args.recent_trading_days,
            ensemble_config=args.ensemble_config.resolve() if args.ensemble_config else None,
            size_floor=size_floor,
            size_cap=size_cap,
            neutral_size_scalar=neutral_size_scalar,
        )
        leg_off = _build_probe_leg(
            bundle_path=bundle_off_path,
            hypothesis_out=hyp_off,
            score_out=score_off,
            hit_out=hit_off,
            recent_days=args.recent_trading_days,
            ensemble_config=args.ensemble_config.resolve() if args.ensemble_config else None,
            size_floor=size_floor,
            size_cap=size_cap,
            neutral_size_scalar=neutral_size_scalar,
        )

        hr_on = _safe_float((leg_on.get("hit_rate_metrics") or {}).get("price_directional_hit_rate"))
        hr_off = _safe_float((leg_off.get("hit_rate_metrics") or {}).get("price_directional_hit_rate"))
        delta_hr = None if hr_on is None or hr_off is None else round(hr_on - hr_off, 6)
        ws_on = _safe_float(leg_on.get("weighted_score"))
        ws_off = _safe_float(leg_off.get("weighted_score"))
        delta_ws = None if ws_on is None or ws_off is None else round(ws_on - ws_off, 6)
        sz_on = _safe_float(((leg_on.get("size_policy") or {}).get("size_scalar")))
        sz_off = _safe_float(((leg_off.get("size_policy") or {}).get("size_scalar")))
        delta_size = None if sz_on is None or sz_off is None else round(sz_on - sz_off, 6)
        swp_on = _safe_float(((leg_on.get("size_policy") or {}).get("payoff_mean_size_weighted")))
        swp_off = _safe_float(((leg_off.get("size_policy") or {}).get("payoff_mean_size_weighted")))
        delta_size_weighted_payoff_mean = None if swp_on is None or swp_off is None else round(swp_on - swp_off, 8)

        prediction_changed = (
            leg_on.get("prediction_direction") != leg_off.get("prediction_direction")
            or leg_on.get("prediction_confidence") != leg_off.get("prediction_confidence")
        )
        observed_impact = bool(
            prediction_changed
            or (delta_hr not in (None, 0.0))
            or (delta_ws not in (None, 0.0))
            or (delta_size not in (None, 0.0))
            or (delta_size_weighted_payoff_mean not in (None, 0.0))
        )

        out = {
            "schema": "compression_bridge_impact_probe_v1",
            "generated_at_utc": _utc_now(),
            "inputs": {
                "bundle_on": str(args.bundle_json.resolve()),
                "bundle_off_synthesized": "compression_bridge_context removed from artifacts/artifact_paths",
                "ensemble_config": str(args.ensemble_config.resolve()) if args.ensemble_config else None,
                "recent_trading_days": max(1, int(args.recent_trading_days)),
                "size_policy": {
                    "mode": "confidence_only_scalar_v1",
                    "size_floor": round(size_floor, 6),
                    "size_cap": round(size_cap, 6),
                    "neutral_size_scalar": round(neutral_size_scalar, 6),
                },
            },
            "legs": {"bridge_on": leg_on, "bridge_off": leg_off},
            "comparison": {
                "prediction_changed": prediction_changed,
                "delta_weighted_score": delta_ws,
                "delta_price_directional_hit_rate": delta_hr,
                "delta_size_scalar": delta_size,
                "delta_size_weighted_payoff_mean": delta_size_weighted_payoff_mean,
                "observed_impact": observed_impact,
            },
            "decision": "OBSERVED_DIFF" if observed_impact else "NO_OBSERVED_DIFF",
            "fact_safe_note": "This probe compares ON/OFF wiring effect under current rule-based generator; "
            "it is not a promotion decision by itself.",
            "out_of_scope": "No live trading trigger; no automatic Track A/B promotion.",
        }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

