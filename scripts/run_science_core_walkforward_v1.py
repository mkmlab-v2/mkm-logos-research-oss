#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Science Core rolling walk-forward combo prefilter [HYPO][research_only].

Selects best science combo on train window (short_1d soft), scores on test window.
Short calendar defaults suit 2026 KOSPI shock study (~40d train / 15d test).
"""
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

import scripts.run_three_lens_horizon_empirical_eval_v1 as v1  # noqa: E402
from scripts.btrack_multilens_per_date_core_v1 import (  # noqa: E402
    DEFAULT_LOGOS_LENS,
    DEFAULT_MYEONGNI_JSONL,
    DEFAULT_SASANG_JSONL,
)
from scripts.run_science_core_holdout_combo_v1 import (  # noqa: E402
    COMBO_LENS_IDS,
    HOLDOUT_REQUIRED_HORIZONS,
    _best_combo_short,
)
from scripts.run_science_core_horizon_empirical_eval_v1 import (  # noqa: E402
    DEFAULT_SCIENCE_JSONL_KOSPI,
    _ensure_science_jsonl,
    run_eval,
)

DEFAULT_OUT = ROOT / "reports/science_core_walkforward_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/science_core_walkforward_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _soft_short(matrix: dict[str, Any], lens_id: str) -> float | None:
    block = (matrix.get(lens_id) or {}).get("short_1d") or {}
    v = block.get("soft_hit_rate")
    return float(v) if v is not None else None


def run_walkforward(
    *,
    kospi_csv: Path,
    science_jsonl: Path,
    train_days: int,
    test_days: int,
    step_days: int,
    max_window_days: int | None,
    date_from: str | None,
    date_to: str | None,
    neutral_bps: float,
    myeongni_jsonl: Path,
    sasang_jsonl: Path,
    logos_lens: Path,
    logos_jsonl: Path | None = None,
    myeongni_momentum_window: int,
) -> dict[str, Any]:
    closes = v1._load_closes(kospi_csv)
    dates = sorted(closes.keys())
    if date_from:
        dates = [d for d in dates if d >= date_from]
    if date_to:
        dates = [d for d in dates if d <= date_to]
    if not dates:
        raise RuntimeError("No KOSPI dates loaded")
    if max_window_days and max_window_days > 0 and len(dates) > max_window_days:
        dates = dates[-max_window_days:]

    common = dict(
        instrument="kospi",
        csv_path=kospi_csv,
        science_jsonl=science_jsonl,
        neutral_bps=neutral_bps,
        myeongni_jsonl=myeongni_jsonl,
        sasang_jsonl=sasang_jsonl,
        logos_lens=logos_lens,
        logos_jsonl=logos_jsonl,
        myeongni_momentum_window=myeongni_momentum_window,
    )

    folds: list[dict[str, Any]] = []
    pos = train_days
    while pos + test_days <= len(dates):
        train_from = dates[pos - train_days]
        train_to = dates[pos - 1]
        test_from = dates[pos]
        test_to = dates[pos + test_days - 1]

        train_doc = run_eval(date_from=train_from, date_to=train_to, **common)
        test_doc = run_eval(
            date_from=test_from,
            date_to=test_to,
            required_horizons=HOLDOUT_REQUIRED_HORIZONS,
            **common,
        )
        train_pick = _best_combo_short(train_doc.get("rate_matrix") or {})
        selected = str(train_pick.get("best_lens_id") or "science_core")
        test_matrix = test_doc.get("rate_matrix") or {}

        test_ranked: list[tuple[str, float]] = []
        for lid in COMBO_LENS_IDS:
            soft = _soft_short(test_matrix, lid)
            if soft is not None:
                test_ranked.append((lid, soft))
        test_ranked.sort(key=lambda x: x[1], reverse=True)
        test_best_id = test_ranked[0][0] if test_ranked else None
        selected_soft = _soft_short(test_matrix, selected)
        science_soft = _soft_short(test_matrix, "science_core")
        uplift = round(selected_soft - science_soft, 4) if selected_soft is not None and science_soft is not None else None

        folds.append(
            {
                "train_window": {"date_from": train_from, "date_to": train_to},
                "test_window": {"date_from": test_from, "date_to": test_to},
                "selected_from_train": selected,
                "train_selection": train_pick,
                "selected_test_short_1d_soft": selected_soft,
                "science_alone_test_short_1d_soft": science_soft,
                "test_uplift_vs_science_alone": uplift,
                "test_best_combo": test_best_id,
                "test_best_short_1d_soft": test_ranked[0][1] if test_ranked else None,
                "selection_hits_test_top1": bool(test_best_id and test_best_id == selected),
                "test_n_eval_dates": test_doc.get("n_eval_dates"),
            }
        )
        pos += step_days

    by_combo: dict[str, list[float]] = {}
    uplifts: list[float] = []
    top1_hits = 0
    for f in folds:
        vid = str(f.get("selected_from_train") or "")
        soft = f.get("selected_test_short_1d_soft")
        if vid and soft is not None:
            by_combo.setdefault(vid, []).append(float(soft))
        u = f.get("test_uplift_vs_science_alone")
        if u is not None:
            uplifts.append(float(u))
        if f.get("selection_hits_test_top1"):
            top1_hits += 1

    variant_rank = sorted(
        (
            {
                "lens_id": vid,
                "n_folds": len(vals),
                "mean_test_short_1d_soft": round(mean(vals), 4),
            }
            for vid, vals in by_combo.items()
        ),
        key=lambda x: (float(x["mean_test_short_1d_soft"]), int(x["n_folds"])),
        reverse=True,
    )

    return {
        "schema": "science_core_walkforward_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "track_wall": "no_track_a_live_auto_merge",
        "instrument": "kospi",
        "available_calendar_days": len(sorted(v1._load_closes(kospi_csv).keys())),
        "effective_window_days": len(dates),
        "eval_window": {"from": dates[0] if dates else None, "to": dates[-1] if dates else None},
        "config": {
            "train_days": train_days,
            "test_days": test_days,
            "step_days": step_days,
            "max_window_days": max_window_days,
            "date_from": date_from,
            "date_to": date_to,
            "required_test_horizons": list(HOLDOUT_REQUIRED_HORIZONS),
        },
        "folds": folds,
        "summary": {
            "n_folds": len(folds),
            "selection_top1_hit_rate": round(top1_hits / len(folds), 4) if folds else None,
            "mean_test_uplift_vs_science_alone": round(mean(uplifts), 4) if uplifts else None,
            "variant_rank_by_test_mean_soft": variant_rank,
            "recommended_prefilter_combos_top2": [v["lens_id"] for v in variant_rank[:2]],
            "note_ko": "Walk-forward는 science 조합 후보 압축용. attach/holdout gate + human signoff 필수.",
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kospi-csv", type=Path, default=v1.KOSPI_CSV)
    ap.add_argument("--science-jsonl", type=Path, default=DEFAULT_SCIENCE_JSONL_KOSPI)
    ap.add_argument("--train-days", type=int, default=40)
    ap.add_argument("--test-days", type=int, default=15)
    ap.add_argument("--step-days", type=int, default=12)
    ap.add_argument("--max-window-days", type=int, default=0, help="0=all available")
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    ap.add_argument("--rebuild-science", action="store_true")
    ap.add_argument("--date-from", type=str, default="2026-01-01")
    ap.add_argument("--date-to", type=str, default="2026-06-08")
    ap.add_argument("--myeongni-jsonl", type=Path, default=DEFAULT_MYEONGNI_JSONL)
    ap.add_argument("--sasang-jsonl", type=Path, default=DEFAULT_SASANG_JSONL)
    ap.add_argument("--logos-lens", type=Path, default=DEFAULT_LOGOS_LENS)
    ap.add_argument("--logos-jsonl", type=Path, default=None)
    ap.add_argument("--myeongni-momentum-window", type=int, default=5)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact-output", type=Path, default=ART_OUT)
    args = ap.parse_args(argv)

    if not args.kospi_csv.is_file():
        print(f"Missing KOSPI CSV: {args.kospi_csv}", file=sys.stderr)
        return 1

    if args.rebuild_science or not args.science_jsonl.is_file():
        _ensure_science_jsonl(
            instrument="kospi",
            csv_path=args.kospi_csv,
            out_path=args.science_jsonl,
            date_from=args.date_from,
            date_to=args.date_to,
            apply_overnight=True,
        )

    doc = run_walkforward(
        kospi_csv=args.kospi_csv,
        science_jsonl=args.science_jsonl,
        train_days=args.train_days,
        test_days=args.test_days,
        step_days=args.step_days,
        max_window_days=args.max_window_days or None,
        date_from=args.date_from,
        date_to=args.date_to,
        neutral_bps=args.neutral_bps,
        myeongni_jsonl=args.myeongni_jsonl,
        sasang_jsonl=args.sasang_jsonl,
        logos_lens=args.logos_lens,
        logos_jsonl=args.logos_jsonl,
        myeongni_momentum_window=args.myeongni_momentum_window,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.artifact_output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.output.write_text(payload, encoding="utf-8")
    args.artifact_output.write_text(payload, encoding="utf-8")

    s = doc["summary"]
    print(
        f"WROTE: {args.output.resolve()} folds={s.get('n_folds')} "
        f"top1={s.get('selection_top1_hit_rate')} uplift={s.get('mean_test_uplift_vs_science_alone')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
