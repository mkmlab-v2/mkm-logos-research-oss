#!/usr/bin/env python3
"""Bridge role-router backtest result to limited-live engine handoff.

Flow:
1) role-router backtest json -> limited-live candidate json
2) candidate json + signoff -> engine input json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_ROLE_ROUTER = ART / "prophecy_lens_role_router_backtest_v1_latest.json"
DEFAULT_ROLE_ROUTER_OPT = ART / "prophecy_role_router_multiscenario_opt_v1_latest.json"
DEFAULT_SIGNOFF = ART / "promotion_signoff_decision_latest.json"
DEFAULT_CANDIDATE_OUT = ART / "btc_top1_limited_live_candidate_from_role_router_latest.json"
DEFAULT_ENGINE_OUT = ART / "btc_limited_live_engine_input_from_role_router_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_candidate_from_source(
    doc: dict[str, Any], source_path: Path, *, min_candidate_days: int
) -> tuple[dict[str, Any], dict[str, Any]]:
    schema = str(doc.get("schema") or "")
    if schema == "prophecy_role_router_multiscenario_opt_v1":
        selected = (doc.get("best_candidate") or {}) if isinstance(doc, dict) else {}
        top_candidates = doc.get("top_candidates") or []
        if isinstance(top_candidates, list):
            for cand in top_candidates:
                if not isinstance(cand, dict):
                    continue
                oos_m = cand.get("oos_metrics") or {}
                if int(oos_m.get("n_days") or 0) >= int(min_candidate_days):
                    selected = cand
                    break
        params = (selected.get("params") or {}) if isinstance(selected, dict) else {}
        metrics = (selected.get("oos_metrics") or {}) if isinstance(selected, dict) else {}
        return (
            {
                "source": str(source_path.resolve()),
                "params": {
                    "router_type": "role_mapping_optimized",
                    **params,
                },
                "metrics": metrics,
                "delta_vs_baseline": None,
            },
            metrics,
        )
    # default: plain role-router backtest artifact
    metrics = (doc.get("metrics") or {}) if isinstance(doc, dict) else {}
    return (
        {
            "source": str(source_path.resolve()),
            "params": {
                "router_type": "role_mapping",
                "logos": "regime_gate",
                "myeongni": "base_direction",
                "sasang": "position_strength_overlay",
            },
            "metrics": metrics,
            "delta_vs_baseline": None,
        },
        metrics,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--role-router-json", type=Path, default=DEFAULT_ROLE_ROUTER_OPT)
    ap.add_argument("--signoff-json", type=Path, default=DEFAULT_SIGNOFF)
    ap.add_argument("--candidate-out", type=Path, default=DEFAULT_CANDIDATE_OUT)
    ap.add_argument("--engine-out", type=Path, default=DEFAULT_ENGINE_OUT)
    ap.add_argument("--symbol", type=str, default="BTCUSDT")
    ap.add_argument("--min-candidate-days", type=int, default=20)
    ap.add_argument("--base-position-usd", type=float, default=100.0)
    ap.add_argument("--limited-live-ratio", type=float, default=0.1)
    ap.add_argument("--max-consecutive-losses", type=int, default=3)
    ap.add_argument("--max-drawdown-pct", type=float, default=2.0)
    ap.add_argument("--approve-submit", action="store_true")
    ap.add_argument("--dry-run", action="store_true", default=True)
    args = ap.parse_args()

    router = _read(args.role_router_json)
    candidate_block, metrics = _extract_candidate_from_source(
        router, args.role_router_json, min_candidate_days=max(1, int(args.min_candidate_days))
    )
    hit_rate = float(metrics.get("directional_hit_rate_active") or 0.0)
    mdd = float(metrics.get("mdd") or 0.0)
    sharpe = float(metrics.get("sharpe") or 0.0)
    n_eval = int(metrics.get("n_days") or 0)
    ratio = max(0.0, min(1.0, float(args.limited_live_ratio)))
    limited_size_usd = round(float(args.base_position_usd) * ratio, 6)

    tradable = n_eval >= int(args.min_candidate_days) and hit_rate >= 0.55 and mdd >= -0.15 and sharpe > 0.0
    candidate_payload = {
        "schema": "btc_top1_limited_live_candidate_from_role_router_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "non_execution": True,
        "candidate": candidate_block,
        "guards": {
            "min_n_days": n_eval >= int(args.min_candidate_days),
            "min_hit_rate_0p55": hit_rate >= 0.55,
            "max_mdd_-0p15": mdd >= -0.15,
            "sharpe_positive": sharpe > 0.0,
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
            "status": "READY_LIMITED_LIVE" if tradable else "HOLD_SHADOW_ONLY",
            "tradable_candidate": tradable,
            "action": "human_review_then_submit_to_engine" if tradable else "keep_shadow_and_recalibrate",
        },
    }
    args.candidate_out.parent.mkdir(parents=True, exist_ok=True)
    args.candidate_out.write_text(json.dumps(candidate_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    adapter = ROOT / "scripts" / "build_btc_limited_live_engine_input_v1.py"
    cmd = [
        sys.executable,
        str(adapter),
        "--candidate-json",
        str(args.candidate_out),
        "--signoff-json",
        str(args.signoff_json),
        "--symbol",
        str(args.symbol),
        "--out",
        str(args.engine_out),
    ]
    if args.approve_submit:
        cmd.append("--approve-submit")
    if args.dry_run:
        cmd.append("--dry-run")
    res = subprocess.run(cmd, cwd=str(ROOT))
    if res.returncode != 0:
        return int(res.returncode)

    print(f"WROTE: {args.candidate_out}")
    print(f"WROTE: {args.engine_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
