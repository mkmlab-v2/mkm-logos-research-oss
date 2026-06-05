#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KOSPI multilens rolling walk-forward backtest (candidate prefilter) [HYPO][research_only]."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
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

DEFAULT_PANEL = ROOT / "reports/btrack_session_myeongni_panel_full_window_v1.csv"
DEFAULT_OUT = ROOT / "reports/kospi_multilens_walkforward_backtest_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/kospi_multilens_walkforward_backtest_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_dates(csv_path: Path) -> list[str]:
    dates: list[str] = []
    with csv_path.open(encoding="utf-8-sig", newline="") as fp:
        for row in csv.DictReader(fp):
            d = str(row.get("Date") or "")[:10]
            if len(d) == 10:
                dates.append(d)
    return sorted(set(dates))


def _build_panel_if_missing(panel_csv: Path, *, date_from: str, date_to: str) -> None:
    if panel_csv.is_file():
        return
    cmd = [
        sys.executable,
        "scripts/build_btrack_session_instant_myeongni_panel_v1.py",
        "--date-from",
        date_from,
        "--date-to",
        date_to,
        "--out-csv",
        str(panel_csv),
    ]
    rc = subprocess.run(cmd, cwd=str(ROOT)).returncode
    if rc != 0:
        raise RuntimeError(f"panel build failed rc={rc}")


def _metrics_tuple(v: dict[str, Any]) -> tuple[float, float, int]:
    m = v.get("metrics") if isinstance(v.get("metrics"), dict) else {}
    return (
        float(m.get("soft_hit_rate") or -1.0),
        float(m.get("directional_hit_rate") or -1.0),
        int(m.get("n_scored") or 0),
    )


def run_walkforward(
    *,
    panel_csv: Path,
    kospi_csv: Path,
    train_days: int,
    test_days: int,
    step_days: int,
    max_window_days: int | None,
) -> dict[str, Any]:
    dates = _load_dates(kospi_csv)
    if not dates:
        raise RuntimeError("No KOSPI dates loaded")
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
        best = train_doc.get("best_variant") or {}
        best_id = str(best.get("variant_id") or "")
        test_rows = train_doc.get("variants") or []
        if best_id:
            # Re-score chosen best on test window
            test_doc = run_backtest(
                panel_by_date=panel_by_date,
                closes=closes,
                date_from=test_from,
                date_to=test_to,
                rules=rules,
                neutral_bps=neutral_bps,
            )
            match = next((r for r in (test_doc.get("variants") or []) if str(r.get("variant_id")) == best_id), None)
            top_test = sorted((test_doc.get("variants") or []), key=_metrics_tuple, reverse=True)
            fold = {
                "train_window": {"date_from": train_from, "date_to": train_to},
                "test_window": {"date_from": test_from, "date_to": test_to},
                "selected_from_train": best_id,
                "selected_test_metrics": (match or {}).get("metrics"),
                "test_best_variant": (top_test[0] if top_test else {}).get("variant_id"),
                "test_best_metrics": (top_test[0] if top_test else {}).get("metrics"),
                "selection_hits_test_top1": bool(top_test and str(top_test[0].get("variant_id")) == best_id),
            }
            folds.append(fold)
        pos += step_days

    by_variant: dict[str, list[float]] = {}
    top1_hits = 0
    for f in folds:
        vid = str(f.get("selected_from_train") or "")
        soft = ((f.get("selected_test_metrics") or {}).get("soft_hit_rate"))
        if vid and soft is not None:
            by_variant.setdefault(vid, []).append(float(soft))
        if f.get("selection_hits_test_top1"):
            top1_hits += 1

    variant_rank = sorted(
        (
            {
                "variant_id": vid,
                "n_folds": len(vals),
                "mean_soft_hit_rate_test": round(mean(vals), 4),
            }
            for vid, vals in by_variant.items()
        ),
        key=lambda x: (float(x["mean_soft_hit_rate_test"]), int(x["n_folds"])),
        reverse=True,
    )

    return {
        "schema": "kospi_multilens_walkforward_backtest_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "track_wall": "no_track_a_live_auto_merge",
        "available_calendar_days": len(_load_dates(kospi_csv)),
        "effective_window_days": len(dates),
        "config": {
            "train_days": train_days,
            "test_days": test_days,
            "step_days": step_days,
            "max_window_days": max_window_days,
        },
        "folds": folds,
        "summary": {
            "n_folds": len(folds),
            "selection_top1_hit_rate": round(top1_hits / len(folds), 4) if folds else None,
            "variant_rank_by_test_mean_soft": variant_rank,
            "recommended_prefilter_variants_top2": [v["variant_id"] for v in variant_rank[:2]],
            "note_ko": "Walk-forward는 후보 압축 용도. 최종 apply는 June forward gate + human signoff 필수.",
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--panel-csv", type=Path, default=DEFAULT_PANEL)
    ap.add_argument("--kospi-csv", type=Path, default=KOSPI_CSV)
    ap.add_argument("--train-days", type=int, default=756, help="~3y trading days")
    ap.add_argument("--test-days", type=int, default=252, help="~1y trading days")
    ap.add_argument("--step-days", type=int, default=126, help="~6m step")
    ap.add_argument("--max-window-days", type=int, default=0, help="0=all available")
    ap.add_argument("--auto-build-panel", action="store_true")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    if not args.kospi_csv.is_file():
        print(f"Missing KOSPI CSV: {args.kospi_csv}", file=sys.stderr)
        return 2
    all_dates = _load_dates(args.kospi_csv)
    if len(all_dates) < (args.train_days + args.test_days):
        print("Not enough data for configured train/test days", file=sys.stderr)
        return 2

    if args.auto_build_panel:
        _build_panel_if_missing(args.panel_csv, date_from=all_dates[0], date_to=all_dates[-1])
    if not args.panel_csv.is_file():
        print(f"Missing panel CSV: {args.panel_csv}", file=sys.stderr)
        return 2

    max_days = args.max_window_days if args.max_window_days > 0 else None
    doc = run_walkforward(
        panel_csv=args.panel_csv,
        kospi_csv=args.kospi_csv,
        train_days=args.train_days,
        test_days=args.test_days,
        step_days=args.step_days,
        max_window_days=max_days,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ART_OUT.parent.mkdir(parents=True, exist_ok=True)
    ART_OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    s = doc.get("summary") or {}
    print(
        f"WROTE: {args.output.resolve()} folds={s.get('n_folds')} "
        f"top1_hit={s.get('selection_top1_hit_rate')} top2={s.get('recommended_prefilter_variants_top2')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
