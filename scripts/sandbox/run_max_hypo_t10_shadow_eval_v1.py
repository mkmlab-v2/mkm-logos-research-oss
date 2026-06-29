#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[MAX_HYPO][HYPO] T10 overlay shadow eval — sandbox-only; no operational *_latest writes.

Loads recommended tier params from max_hypo_recommended_tier_manifest_v1.json (or CLI overrides),
applies ``mild_and_range_or_composite_conservative_bull_to_bear_rebound_guard_v0`` on multilens
operational baseline rows, and writes under ``experiments/max_hypo_unbound/results/`` only.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SANDBOX_ROOT = ROOT / "experiments" / "max_hypo_unbound"
DEFAULT_MANIFEST = SANDBOX_ROOT / "results" / "max_hypo_recommended_tier_manifest_v1.json"
DEFAULT_RECIPE = SANDBOX_ROOT / "max_hypo_recipe_v1.json"
DEFAULT_OUT = SANDBOX_ROOT / "results" / "max_hypo_t10_shadow_eval_v1_latest.json"
DEFAULT_PANEL = ROOT / "reports/btrack_session_myeongni_panel_252d_v1.csv"
KOSPI_CSV = ROOT / "research/market_data/kospi_daily_external_yf.csv"

FORBIDDEN_OUTPUTS = frozenset(
    {
        "docs/final/artifacts/btrack_prophecy_score_latest.json",
        "docs/final/artifacts/prophecy_hit_rate_eval_latest.json",
        "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json",
    }
)

T10_OVERLAY = "mild_and_range_or_composite_conservative_bull_to_bear_rebound_guard_v0"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def assert_output_path_isolated(out_path: Path) -> None:
    rel = _rel(out_path.resolve()).replace("\\", "/").lower()
    for forbidden in FORBIDDEN_OUTPUTS:
        if rel == forbidden.lower() or rel.endswith(forbidden.lower().split("/")[-1]):
            raise ValueError(f"forbidden operational output path: {rel}")


def _latest_kospi_date(kospi_csv: Path) -> str | None:
    if not kospi_csv.is_file():
        return None
    lines = kospi_csv.read_text(encoding="utf-8", errors="replace").strip().splitlines()
    for line in reversed(lines):
        line = line.strip()
        if not line or line.lower().startswith("date"):
            continue
        return line.split(",")[0].strip()[:10]
    return None


def _load_manifest_params(manifest_path: Path) -> dict[str, Any]:
    doc = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    rec = doc.get("recommended") if isinstance(doc.get("recommended"), dict) else {}
    params = rec.get("params") if isinstance(rec.get("params"), dict) else {}
    return {
        "tier_id": rec.get("tier_id"),
        "overlay": rec.get("overlay") or T10_OVERLAY,
        "prior_mild_threshold": float(params.get("prior_mild_threshold") or -0.04),
        "rebound_guard_threshold": float(params.get("rebound_guard_threshold") or -0.075),
        "prior_range_low_threshold": float(params.get("prior_range_low_threshold") or 0.15),
        "session_open_composite_overnight_threshold": float(
            params.get("session_open_composite_overnight_threshold") or -0.025
        ),
        "manifest_path": _rel(manifest_path),
    }


def run_shadow_eval(
    *,
    recipe_path: Path,
    manifest_path: Path,
    panel_csv: Path,
    kospi_csv: Path,
    date_from: str,
    date_to: str,
    spotlight_dates: list[str],
    out_path: Path,
) -> dict[str, Any]:
    from scripts.run_prophecy_restoration_spike import (
        _overnight_return_by_eval_date,
        _prior_completed_daily_return_by_eval_date,
        _prior_range_position_by_eval_date,
    )
    from scripts.sandbox.run_max_theory_unbound_simulation_v1 import (
        _overlay_delta_on_rows,
        _spotlight_for_overlay,
        build_multilens_eval_rows,
        load_recipe,
    )

    assert_output_path_isolated(out_path.resolve())
    recipe = load_recipe(recipe_path)
    tier = _load_manifest_params(manifest_path)
    overlay = str(tier.get("overlay") or T10_OVERLAY)
    mild_t = float(tier["prior_mild_threshold"])
    guard_t = float(tier["rebound_guard_threshold"])
    range_t = float(tier["prior_range_low_threshold"])
    ovn_t = float(tier["session_open_composite_overnight_threshold"])

    rows_in = build_multilens_eval_rows(
        recipe=recipe,
        panel_csv=panel_csv,
        kospi_csv=kospi_csv,
        date_from=date_from,
        date_to=date_to,
        variant_key="operational_baseline",
    )
    if not rows_in:
        raise SystemExit("no multilens eval rows in window")

    prior_map = _prior_completed_daily_return_by_eval_date(kospi_csv)
    overnight_map = _overnight_return_by_eval_date(kospi_csv)
    range_map = _prior_range_position_by_eval_date(kospi_csv)

    base_rate, ov_rate, delta, overlaid = _overlay_delta_on_rows(
        rows_in,
        overlay=overlay,
        prior_map=prior_map,
        overnight_map=overnight_map,
        intraday_map=None,
        prior_return_threshold=mild_t,
        rebound_guard_threshold=guard_t,
        session_open_composite_overnight_threshold=ovn_t,
        range_position_map=range_map,
        prior_range_low_threshold=range_t,
    )
    spotlight = _spotlight_for_overlay(
        rows_in=rows_in,
        overlaid=overlaid,
        prior_map=prior_map,
        overnight_map=overnight_map,
        intraday_drawdown_map=None,
        spotlight_dates=spotlight_dates,
        range_position_map=range_map,
    )
    spotlight_safe = all(
        sp.get("after_overlay_hit") is True
        for sp in spotlight
        if sp.get("date") and "status" not in sp
    )

    payload: dict[str, Any] = {
        "schema": "max_hypo_t10_shadow_eval_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "hypothesis_tag": "[MAX_HYPO][HYPO]",
        "shadow_lane": "max_hypo_t10_overlay",
        "tier_id": tier.get("tier_id"),
        "overlay": overlay,
        "params": {
            "prior_mild_threshold": mild_t,
            "rebound_guard_threshold": guard_t,
            "prior_range_low_threshold": range_t,
            "session_open_composite_overnight_threshold": ovn_t,
        },
        "manifest_path": tier.get("manifest_path"),
        "window": {"date_from": date_from, "date_to": date_to},
        "n_evaluated": len(rows_in),
        "baseline_hit_rate": base_rate,
        "shadow_hit_rate": ov_rate,
        "delta_hit_rate": delta,
        "spotlight_dates": spotlight_dates,
        "spotlight": spotlight,
        "spotlight_safe": spotlight_safe,
        "track_wall": "no_track_a_live_auto_merge",
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--recipe-json", type=Path, default=DEFAULT_RECIPE)
    ap.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--panel-csv", type=Path, default=DEFAULT_PANEL)
    ap.add_argument("--kospi-csv", type=Path, default=KOSPI_CSV)
    ap.add_argument("--date-from", default="2025-05-26")
    ap.add_argument("--date-to", default="")
    ap.add_argument(
        "--spotlight-dates",
        default="2026-06-08,2026-06-09",
        help="Comma-separated; use --include-latest-kospi-day to append last CSV row date.",
    )
    ap.add_argument(
        "--include-latest-kospi-day",
        action="store_true",
        help="Append latest trading date from kospi CSV to spotlight (6/10+ refresh).",
    )
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    date_to = str(args.date_to).strip() or (_latest_kospi_date(args.kospi_csv) or "2026-06-09")
    spotlight = [d.strip()[:10] for d in str(args.spotlight_dates).split(",") if d.strip()]
    if args.include_latest_kospi_day:
        latest = _latest_kospi_date(args.kospi_csv)
        if latest and latest not in spotlight:
            spotlight.append(latest)

    payload = run_shadow_eval(
        recipe_path=args.recipe_json,
        manifest_path=args.manifest_json,
        panel_csv=args.panel_csv,
        kospi_csv=args.kospi_csv,
        date_from=str(args.date_from)[:10],
        date_to=date_to[:10],
        spotlight_dates=spotlight,
        out_path=args.output,
    )
    print(f"WROTE: {args.output.resolve()}")
    print(
        f"  shadow delta={payload.get('delta_hit_rate')} "
        f"spotlight_safe={payload.get('spotlight_safe')} "
        f"n={payload.get('n_evaluated')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
