#!/usr/bin/env python3
"""Prophecy direction overlay ablation spike (B-track measurement harness).

Computes directional hit-rate before/after applying an optional rule-based overlay on the
same ``rows[]`` as ``eval_prophecy_hit_rate_v1.py`` price mode. Intended for comparing
policy variants — **not** a production trading trigger and **not** biblical/Myeongri fusion.

Overlays:

- ``prior_day_shock_bear_abstain_v0`` (**default**): load KOSPI CSV; for each ``eval_date``,
  use the **prior completed daily return** (close[i-1] vs close[i-2] before eval session i)
  — no lookahead into the eval day's ``daily_return``. If prior return <= threshold and
  prediction is ``bear``, downgrade to ``neutral`` ([HYPO] liquidity-shock abstention toy).

- ``stress_bear_to_neutral_v0``: calendar stress years from a year-map JSON
  (sample ``4d_to_ohaeng_regime_year_map_sample_v1.json``); ``bear→neutral`` in-window.

Outputs: ``docs/final/artifacts/prophecy_restoration_spike_latest.json``
Schema: ``prophecy_overlay_ablation_spike_v1``
"""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_latest.json"
DEFAULT_YEAR_MAP = ROOT / "docs" / "final" / "artifacts" / "4d_to_ohaeng_regime_year_map_sample_v1.json"
DEFAULT_KOSPI_CSV = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "prophecy_restoration_spike_latest.json"
SCHEMA = "prophecy_overlay_ablation_spike_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _eval_directional_hit(rows: list[dict[str, Any]]) -> tuple[float | None, int, int]:
    hits = 0
    n = 0
    for r in rows:
        pd = str(r.get("predicted_direction") or r.get("predicted_sign") or "").strip().lower()
        ad = str(r.get("actual_direction") or r.get("actual_sign") or "").strip().lower()
        if not pd or not ad:
            continue
        if pd not in ("bull", "bear", "neutral") or ad not in ("bull", "bear", "neutral"):
            continue
        n += 1
        if pd == ad:
            hits += 1
    if n == 0:
        return None, 0, 0
    return round(hits / n, 6), n, hits


def _stress_years_from_map(doc: dict[str, Any]) -> set[int]:
    out: set[int] = set()
    rows = doc.get("rows")
    if not isinstance(rows, list):
        return out
    for r in rows:
        if not isinstance(r, dict):
            continue
        try:
            sy = int(r.get("start_year"))
            ey = int(r.get("end_year"))
        except (TypeError, ValueError):
            continue
        for y in range(sy, ey + 1):
            out.add(y)
    return out


def _eval_year(eval_date: str) -> int | None:
    s = str(eval_date or "").strip()
    if len(s) < 4 or not s[:4].isdigit():
        return None
    return int(s[:4])


def _prior_completed_daily_return_by_eval_date(csv_path: Path) -> dict[str, float]:
    """Map eval_date (YYYY-MM-DD) → prior trading session's simple close-to-close return.

    For CSV row index i (sorted ascending dates), eval_date = date[i]. The last fully
    observed daily return before that session starts is (close[i-1]-close[i-2])/close[i-2].
    """
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.logos_shadow_eval_lib import load_kospi_yf_rows

    rows = load_kospi_yf_rows(csv_path)
    if len(rows) < 3:
        return {}
    out: dict[str, float] = {}
    for i in range(2, len(rows)):
        ed = str(rows[i]["date"])[:10]
        try:
            c1 = float(rows[i - 1]["close"])
            c2 = float(rows[i - 2]["close"])
        except (TypeError, ValueError):
            continue
        if c2 == 0.0:
            continue
        out[ed] = (c1 - c2) / c2
    return out


def _apply_overlay(
    rows: list[dict[str, Any]],
    *,
    overlay: str,
    stress_years: set[int],
    prior_return_by_date: dict[str, float] | None,
    prior_return_threshold: float,
) -> tuple[list[dict[str, Any]], int]:
    """Return new rows (deep copy) and count of modified predictions."""
    modified = 0
    out: list[dict[str, Any]] = []
    prior_return_by_date = prior_return_by_date or {}
    for r in rows:
        nr = deepcopy(r)
        pred = str(nr.get("predicted_direction") or "").strip().lower()
        ed = str(nr.get("eval_date") or "").strip()[:10]
        year = _eval_year(ed)
        if overlay == "none":
            pass
        elif overlay == "stress_bear_to_neutral_v0":
            if (
                year is not None
                and year in stress_years
                and pred == "bear"
            ):
                nr["predicted_direction"] = "neutral"
                nr["overlay_rule"] = "stress_bear_to_neutral_v0"
                modified += 1
        elif overlay == "prior_day_shock_bear_abstain_v0":
            pr = prior_return_by_date.get(ed)
            if pr is not None and pred == "bear" and pr <= prior_return_threshold:
                nr["predicted_direction"] = "neutral"
                nr["overlay_rule"] = "prior_day_shock_bear_abstain_v0"
                nr["overlay_prior_completed_daily_return"] = round(pr, 8)
                nr["overlay_prior_threshold"] = prior_return_threshold
                modified += 1
        else:
            raise ValueError(f"unknown overlay: {overlay}")
        out.append(nr)
    return out, modified


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Prophecy overlay ablation spike — same rows; optional bear→neutral overlays.",
    )
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE, help="btrack_prophecy_score_v1 JSON.")
    ap.add_argument(
        "--year-map-json",
        type=Path,
        default=DEFAULT_YEAR_MAP,
        help="JSON with schema like 4d_to_ohaeng_regime_year_map_sample_v1 (rows start_year/end_year).",
    )
    ap.add_argument(
        "--kospi-csv",
        type=Path,
        default=DEFAULT_KOSPI_CSV,
        help="KOSPI daily CSV (for prior_day_shock_bear_abstain_v0).",
    )
    ap.add_argument(
        "--prior-return-threshold",
        type=float,
        default=-0.048,
        help=(
            "prior_day overlay: bear→neutral when prior completed daily return <= this "
            "(default -4.8%%: aligns with sweep best_delta on OHLCV-30 panel as of "
            "prophecy_overlay_prior_threshold_recommended_latest.json — re-sweep after panel changes)."
        ),
    )
    ap.add_argument(
        "--overlay",
        choices=("none", "stress_bear_to_neutral_v0", "prior_day_shock_bear_abstain_v0"),
        default="prior_day_shock_bear_abstain_v0",
        help="Overlay policy (default: prior-day shock abstention using KOSPI CSV).",
    )
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    score_doc = _load_json(args.score_json)
    if not score_doc:
        print(f"ERROR: missing or invalid score-json: {args.score_json}", flush=True)
        return 2

    raw_rows = score_doc.get("rows")
    if isinstance(raw_rows, list):
        rows_in = [r for r in raw_rows if isinstance(r, dict)]
    else:
        rows_in = [score_doc]

    ym = _load_json(args.year_map_json) or {}
    stress_years = _stress_years_from_map(ym)

    prior_map: dict[str, float] | None = None
    if args.overlay == "prior_day_shock_bear_abstain_v0":
        if not args.kospi_csv.is_file():
            print(f"ERROR: --kospi-csv not found: {args.kospi_csv}", flush=True)
            return 3
        prior_map = _prior_completed_daily_return_by_eval_date(args.kospi_csv)

    base_rate, base_n, base_hits = _eval_directional_hit(rows_in)
    overlaid, n_mod = _apply_overlay(
        rows_in,
        overlay=args.overlay,
        stress_years=stress_years,
        prior_return_by_date=prior_map,
        prior_return_threshold=float(args.prior_return_threshold),
    )
    ov_rate, ov_n, ov_hits = _eval_directional_hit(overlaid)

    delta = None
    if base_rate is not None and ov_rate is not None:
        delta = round(ov_rate - base_rate, 6)

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {
            "score_json": str(args.score_json),
            "year_map_json": str(args.year_map_json),
            "overlay": args.overlay,
            "stress_years_resolved": sorted(stress_years),
            "kospi_csv": str(args.kospi_csv) if args.overlay == "prior_day_shock_bear_abstain_v0" else None,
            "prior_return_threshold": args.prior_return_threshold
            if args.overlay == "prior_day_shock_bear_abstain_v0"
            else None,
        },
        "baseline": {
            "price_directional_hit_rate": base_rate,
            "n_evaluated": base_n,
            "hits": base_hits,
        },
        "after_overlay": {
            "price_directional_hit_rate": ov_rate,
            "n_evaluated": ov_n,
            "hits": ov_hits,
            "overlay_rows_modified": n_mod,
        },
        "delta_hit_rate": delta,
        "notes": [
            "Same scoring rules as eval_prophecy_hit_rate_v1 price mode over rows[].",
            "Overlay is a measurement placeholder — not admission to Track A / live routing.",
            "stress_bear_to_neutral_v0: panels only in non-stress years show delta_hit_rate≈0 by construction.",
            "prior_day_shock_bear_abstain_v0: uses prior completed daily return from KOSPI CSV only (no eval-day lookahead).",
        ],
    }

    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    print(text)
    if not args.stdout_only:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(f"WROTE: {args.output.resolve()}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
