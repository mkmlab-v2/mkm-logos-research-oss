#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stochastic forward foreign-flow sensitivity for composite shadow [HYPO].

Separate arm — does NOT replace composite_bear_conditional approval path.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_kospi_june2026_conditional_unlock_shadow_v1 import _coord_raw_bull  # noqa: E402
from scripts.build_kospi_june2026_daily_prophecy_calendar_v1 import build_calendar  # noqa: E402
from scripts.build_kospi_june2026_parallel_shadow_bundle_v1 import BEAR_SCENARIO  # noqa: E402
from scripts.kospi_composite_shadow_lib_v1 import composite_bear_conditional as composite_direction  # noqa: E402
from scripts.btrack_daily_hero_board_lib_v1 import predict_slot  # noqa: E402
from scripts.kospi_forward_flow_gate_lib_v1 import evaluate_conditional_unlock  # noqa: E402
from scripts.kospi_krx_calendar_v1 import krx_trading_days  # noqa: E402
from scripts.kospi_weight_counterfactual_lib_v1 import replay_scenario  # noqa: E402

DEFAULT_RULES = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
DEFAULT_FLOW = ROOT / "research/market_data/kospi_daily_flow_external.csv"
DEFAULT_OUT = ROOT / "reports/kospi_forward_flow_stochastic_sensitivity_v1_latest.json"


def _utc() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _flow_stats(flow: dict[str, float | None]) -> dict[str, float]:
    vals = [v for v in flow.values() if v is not None and v != 0.0]
    if not vals:
        return {"mean": 0.0, "std": 50000.0, "n": 0}
    mean = sum(vals) / len(vals)
    var = sum((x - mean) ** 2 for x in vals) / max(1, len(vals) - 1)
    return {"mean": mean, "std": max(1000.0, var**0.5), "n": len(vals)}


def _month_range(from_ym: str, to_ym: str) -> list[str]:
    y0, m0 = map(int, from_ym.split("-"))
    y1, m1 = map(int, to_ym.split("-"))
    out: list[str] = []
    y, m = y0, m0
    while (y, m) <= (y1, m1):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


def _synthetic_flow_for_session(rng: random.Random, stats: dict[str, float]) -> float:
    return rng.gauss(float(stats["mean"]), float(stats["std"]))


def run_path(
    *,
    path_id: int,
    rng: random.Random,
    year_months: list[str],
    rules: dict[str, Any],
    stats: dict[str, float],
    last_real: str,
) -> list[dict[str, Any]]:
    eval_stub: dict[str, Any] = {"rows": []}
    nb = float(rules.get("neutral_band", 0.06))
    bp = rules.get("blend_policy_v2") if isinstance(rules.get("blend_policy_v2"), dict) else {}
    rows: list[dict[str, Any]] = []

    for ym in year_months:
        cal = build_calendar(year_month=ym, skip_panel=True, profile="v2_multilens")
        for cr in cal.get("rows") or []:
            dk = str(cr.get("session_date"))
            if dk <= last_real:
                continue
            active = str(cr.get("predicted_direction") or "neutral")
            bear_triple, _, _ = replay_scenario(
                cr, scenario_id=BEAR_SCENARIO, neutral_band=nb, blend_policy=bp
            )
            coord_raw, _ = _coord_raw_bull(cr, rules, eval_stub)
            shock_pred = bool((predict_slot("macro_news_shock", dk) or {}).get("predicted_binary"))
            prior_fn = _synthetic_flow_for_session(rng, stats)
            allow_unlock, _ = evaluate_conditional_unlock(
                prior_foreign=prior_fn,
                shock_pred=shock_pred,
                foreign_sell_threshold=FOREIGN_SELL_THRESHOLD,
                apply_foreign_flow_gate=True,
            )
            unlock_candidate = active == "neutral" and coord_raw == "bull"
            composite = composite_direction(
                v2=active,
                bear_triple=bear_triple,
                coord_raw=coord_raw,
                unlock_candidate=unlock_candidate,
                cond_allow=allow_unlock,
            )
            rows.append(
                {
                    "path_id": path_id,
                    "session_date": dk,
                    "year_month": ym,
                    "active": active,
                    "composite": composite,
                    "synthetic_prior_foreign": round(prior_fn, 2),
                }
            )
    return rows


def aggregate_paths(all_rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_month: dict[str, list[str]] = {}
    for r in all_rows:
        ym = str(r["year_month"])
        by_month.setdefault(ym, []).append(str(r["composite"]))

    month_summary: list[dict[str, Any]] = []
    for ym in sorted(by_month):
        dirs = by_month[ym]
        counts = Counter(dirs)
        month_summary.append(
            {
                "year_month": ym,
                "n_path_days": len(dirs),
                "bull_share": round(counts.get("bull", 0) / len(dirs), 4),
                "bear_share": round(counts.get("bear", 0) / len(dirs), 4),
                "neutral_share": round(counts.get("neutral", 0) / len(dirs), 4),
            }
        )
    return {"months": month_summary}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--from-month", default="2027-01")
    ap.add_argument("--to-month", default="2028-12")
    ap.add_argument("--n-paths", type=int, default=100)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ns = ap.parse_args()

    from scripts.kospi_forward_flow_gate_lib_v1 import last_flow_observation_date, load_flow_daily

    flow = load_flow_daily(DEFAULT_FLOW)
    last_real = last_flow_observation_date(flow) or "2026-06-26"
    stats = _flow_stats(flow)
    rules = _read(DEFAULT_RULES)
    months = _month_range(ns.from_month, ns.to_month)

    all_rows: list[dict[str, Any]] = []
    for pid in range(ns.n_paths):
        rng = random.Random(ns.seed + pid)
        all_rows.extend(
            run_path(
                path_id=pid,
                rng=rng,
                year_months=months,
                rules=rules,
                stats=stats,
                last_real=last_real,
            )
        )

    doc = {
        "schema": "kospi_forward_flow_stochastic_sensitivity_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "arm": "stochastic_foreign_flow_sensitivity",
        "not_approval_arm": "composite_bear_conditional unchanged",
        "n_paths": ns.n_paths,
        "seed": ns.seed,
        "from_month": ns.from_month,
        "to_month": ns.to_month,
        "last_real_flow_date": last_real,
        "flow_stats": stats,
        "aggregate": aggregate_paths(all_rows),
        "reproduce": (
            f"py scripts/build_kospi_forward_flow_stochastic_sensitivity_v1.py "
            f"--from-month {ns.from_month} --to-month {ns.to_month} --n-paths {ns.n_paths} --seed {ns.seed}"
        ),
    }
    ns.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    art = ROOT / "docs/final/artifacts/kospi_forward_flow_stochastic_sensitivity_v1_latest.json"
    art.parent.mkdir(parents=True, exist_ok=True)
    art.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(ns.output), "n_paths": ns.n_paths}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
