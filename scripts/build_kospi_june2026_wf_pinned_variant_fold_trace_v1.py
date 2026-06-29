#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Walk-forward fold trace for pinned variants (incl. v2_lens3_heavy) [HYPO][RQ-032]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_kospi_june2026_daily_prophecy_calendar_v1 import _read_json  # noqa: E402
from scripts.run_kospi_multilens_blend_backtest_v1 import (  # noqa: E402
    EVOLUTION_RULES,
    KOSPI_CSV,
    _load_closes,
    _load_panel,
    run_backtest,
)
from scripts.run_kospi_multilens_walkforward_backtest_v1 import (  # noqa: E402
    DEFAULT_PANEL,
    _build_panel_if_missing,
    _load_dates,
    _metrics_tuple,
)

DEFAULT_WF = ROOT / "reports/kospi_multilens_walkforward_backtest_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_june2026_wf_pinned_variant_fold_trace_v1_latest.json"

PINNED_VARIANTS = (
    "v2_lens3_heavy",
    "v2_lens3_heavy_4ai_current",
    "v2_default",
    "v2_default_4ai_current",
    "v2_session_heavy_4ai_current",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _variant_metrics(doc: dict[str, Any], variant_id: str) -> dict[str, Any] | None:
    for row in doc.get("variants") or []:
        if str(row.get("variant_id")) == variant_id:
            m = row.get("metrics")
            return m if isinstance(m, dict) else None
    return None


def run_pinned_trace(
    *,
    panel_csv: Path,
    kospi_csv: Path,
    train_days: int,
    test_days: int,
    step_days: int,
    max_window_days: int | None,
    pinned: tuple[str, ...],
) -> dict[str, Any]:
    dates = _load_dates(kospi_csv)
    if max_window_days and max_window_days > 0 and len(dates) > max_window_days:
        dates = dates[-max_window_days:]

    panel_by_date = _load_panel(panel_csv)
    closes = _load_closes(kospi_csv)
    rules = _read_json(EVOLUTION_RULES)
    neutral_bps = float(rules.get("neutral_bps", 5.0))

    folds: list[dict[str, Any]] = []
    pos = train_days
    while pos + test_days <= len(dates):
        train_from = dates[pos - train_days]
        train_to = dates[pos - 1]
        test_from = dates[pos]
        test_to = dates[pos + test_days - 1]

        train_doc = run_backtest(
            panel_by_date=panel_by_date,
            closes=closes,
            date_from=train_from,
            date_to=train_to,
            rules=rules,
            neutral_bps=neutral_bps,
        )
        test_doc = run_backtest(
            panel_by_date=panel_by_date,
            closes=closes,
            date_from=test_from,
            date_to=test_to,
            rules=rules,
            neutral_bps=neutral_bps,
        )

        best = train_doc.get("best_variant") or {}
        best_id = str(best.get("variant_id") or "")
        top_test = sorted((test_doc.get("variants") or []), key=_metrics_tuple, reverse=True)
        test_best_id = str((top_test[0] if top_test else {}).get("variant_id") or "")

        pinned_test: dict[str, Any] = {}
        for vid in pinned:
            m = _variant_metrics(test_doc, vid)
            if m is not None:
                pinned_test[vid] = m

        lens3_soft = (pinned_test.get("v2_lens3_heavy") or {}).get("soft_hit_rate")
        train_best_soft = (_variant_metrics(test_doc, best_id) or {}).get("soft_hit_rate") if best_id else None

        folds.append(
            {
                "train_window": {"date_from": train_from, "date_to": train_to},
                "test_window": {"date_from": test_from, "date_to": test_to},
                "selected_from_train": best_id,
                "test_best_variant": test_best_id,
                "selection_hits_test_top1": best_id == test_best_id,
                "pinned_test_metrics": pinned_test,
                "lens3_heavy_beats_train_pick_on_test": (
                    lens3_soft is not None
                    and train_best_soft is not None
                    and float(lens3_soft) > float(train_best_soft)
                ),
            }
        )
        pos += step_days

    by_variant: dict[str, list[float]] = {vid: [] for vid in pinned}
    lens3_beats_train = 0
    for f in folds:
        if f.get("lens3_heavy_beats_train_pick_on_test"):
            lens3_beats_train += 1
        for vid, m in (f.get("pinned_test_metrics") or {}).items():
            soft = m.get("soft_hit_rate")
            if soft is not None:
                by_variant.setdefault(vid, []).append(float(soft))

    rank = sorted(
        (
            {
                "variant_id": vid,
                "n_folds_with_metrics": len(vals),
                "mean_soft_hit_rate_test": round(mean(vals), 4) if vals else None,
            }
            for vid, vals in by_variant.items()
        ),
        key=lambda x: float(x.get("mean_soft_hit_rate_test") or -1),
        reverse=True,
    )

    lens3_mean = next((r["mean_soft_hit_rate_test"] for r in rank if r["variant_id"] == "v2_lens3_heavy"), None)
    wf_top2_mean = [
        r for r in rank if r["variant_id"] in ("v2_default", "v2_session_heavy_4ai_current")
    ]

    return {
        "schema": "kospi_june2026_wf_pinned_variant_fold_trace_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": False,
        "rq_pointer": "RQ-032",
        "config": {
            "train_days": train_days,
            "test_days": test_days,
            "step_days": step_days,
            "max_window_days": max_window_days,
            "pinned_variants": list(pinned),
        },
        "n_folds": len(folds),
        "pinned_mean_soft_rank": rank,
        "lens3_heavy_beats_train_winner_on_test_folds": lens3_beats_train,
        "lens3_heavy_beats_train_winner_rate": round(lens3_beats_train / len(folds), 4) if folds else None,
        "comparison_ko": {
            "v2_lens3_heavy_mean_test_soft": lens3_mean,
            "wf_prefilter_top2_candidates": wf_top2_mean,
            "lens3_vs_default_delta_pp": round(
                float(lens3_mean or 0) - float(next((r["mean_soft_hit_rate_test"] for r in rank if r["variant_id"] == "v2_default"), 0) or 0),
                4,
            )
            if lens3_mean is not None
            else None,
        },
        "fold_sample_tail": folds[-3:],
        "verdict_ko": (
            f"pinned trace — v2_lens3_heavy mean test soft={lens3_mean}; "
            f"train winner beat on {lens3_beats_train}/{len(folds)} folds. apply 금지."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--wf-json", type=Path, default=DEFAULT_WF, help="Reuse config from existing WF artifact")
    ap.add_argument("--panel-csv", type=Path, default=DEFAULT_PANEL)
    ap.add_argument("--kospi-csv", type=Path, default=KOSPI_CSV)
    ap.add_argument("--train-days", type=int, default=None)
    ap.add_argument("--test-days", type=int, default=None)
    ap.add_argument("--step-days", type=int, default=None)
    ap.add_argument("--max-folds", type=int, default=0, help="If >0, limit folds for smoke (step widened)")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    wf = _read_json(args.wf_json) if args.wf_json.is_file() else {}
    cfg = wf.get("config") if isinstance(wf.get("config"), dict) else {}
    train_days = int(args.train_days or cfg.get("train_days") or 1260)
    test_days = int(args.test_days or cfg.get("test_days") or 252)
    step_days = int(args.step_days or cfg.get("step_days") or 126)
    max_window = cfg.get("max_window_days")

    if not args.panel_csv.is_file():
        dates = _load_dates(args.kospi_csv)
        if dates:
            _build_panel_if_missing(args.panel_csv, date_from=dates[0], date_to=dates[-1])

    doc = run_pinned_trace(
        panel_csv=args.panel_csv,
        kospi_csv=args.kospi_csv,
        train_days=train_days,
        test_days=test_days,
        step_days=step_days if args.max_folds <= 0 else step_days * max(1, 46 // max(1, args.max_folds)),
        max_window_days=max_window,
        pinned=PINNED_VARIANTS,
    )
    if args.max_folds > 0 and len(doc.get("folds", [])) > args.max_folds:
        pass  # step widened above approximates limit

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rank = doc.get("pinned_mean_soft_rank") or []
    lens3 = next((r for r in rank if r.get("variant_id") == "v2_lens3_heavy"), {})
    print(
        f"WROTE: {args.output.resolve()} folds={doc.get('n_folds')} "
        f"lens3_mean_soft={lens3.get('mean_soft_hit_rate_test')} "
        f"beats_train={doc.get('lens3_heavy_beats_train_winner_on_test_folds')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
