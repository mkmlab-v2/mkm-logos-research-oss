#!/usr/bin/env python3
"""Build top-1 limited-live BTC candidate from prophecy artifacts.

Safety policy:
- research signal selection only
- no execution side effects
- enforce guard gates before candidate is marked tradable
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_SWEEP = ART / "prophecy_per_date_lens_combo_sweep_v1_latest.json"
DEFAULT_PROMOTION_GATES = ART / "prophecy_promotion_gates_v1_panel_calibrated_latest.json"
DEFAULT_CAUSAL_GUARD = ART / "prophecy_causal_active_guard_latest.json"
DEFAULT_OUT = ART / "btc_top1_limited_live_candidate_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_float(v: Any, d: float = 0.0) -> float:
    return float(v) if isinstance(v, (int, float)) else d


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sweep-json", type=Path, default=DEFAULT_SWEEP)
    ap.add_argument("--promotion-gates-json", type=Path, default=DEFAULT_PROMOTION_GATES)
    ap.add_argument("--causal-guard-json", type=Path, default=DEFAULT_CAUSAL_GUARD)
    ap.add_argument("--base-position-usd", type=float, default=100.0)
    ap.add_argument("--limited-live-ratio", type=float, default=0.1, help="0.05~0.10 recommended")
    ap.add_argument("--max-consecutive-losses", type=int, default=3)
    ap.add_argument("--max-drawdown-pct", type=float, default=2.0)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    sweep = _read(args.sweep_json)
    gates = _read(args.promotion_gates_json)
    guard = _read(args.causal_guard_json)

    top = (sweep.get("best_candidate") or {})
    metrics = top.get("metrics") or {}
    params = top.get("params") or {}

    hit_rate = _safe_float(metrics.get("price_directional_hit_rate"))
    n_eval = int(metrics.get("n_evaluated") or 0)
    delta_vs_baseline = _safe_float(top.get("delta_vs_baseline"))

    gates_ok = bool(gates.get("all_gates_passed")) and bool(gates.get("strict_passed"))
    guard_ok = bool(guard.get("enforcement_enabled")) and not bool(guard.get("should_rollback"))
    ratio = max(0.0, min(1.0, float(args.limited_live_ratio)))
    limited_size_usd = round(float(args.base_position_usd) * ratio, 6)

    tradable = gates_ok and guard_ok and n_eval >= 30 and hit_rate >= 0.55 and delta_vs_baseline > 0.0
    status = "READY_LIMITED_LIVE" if tradable else "HOLD_SHADOW_ONLY"

    payload = {
        "schema": "btc_top1_limited_live_candidate_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "non_execution": True,
        "candidate": {
            "source": str(args.sweep_json.resolve()),
            "params": params,
            "metrics": metrics,
            "delta_vs_baseline": delta_vs_baseline,
        },
        "guards": {
            "promotion_gates_passed": gates_ok,
            "causal_guard_passed": guard_ok,
            "min_n_evaluated_30": n_eval >= 30,
            "min_hit_rate_0p55": hit_rate >= 0.55,
            "min_delta_vs_baseline_pos": delta_vs_baseline > 0.0,
        },
        "limited_live_policy": {
            "mode": "S4_LIMITED_LIVE",
            "position_ratio": ratio,
            "base_position_usd": float(args.base_position_usd),
            "limited_position_usd": limited_size_usd,
            "max_consecutive_losses": int(args.max_consecutive_losses),
            "max_drawdown_pct": float(args.max_drawdown_pct),
            "auto_scale_up": False,
            "auto_bridge_enabled": False,
            "auto_live_trigger_enabled": False,
        },
        "decision": {
            "status": status,
            "tradable_candidate": tradable,
            "action": "human_review_then_submit_to_engine" if tradable else "keep_shadow_and_recalibrate",
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"status={status}, limited_position_usd={limited_size_usd}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
