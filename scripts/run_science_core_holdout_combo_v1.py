#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Science Core train/holdout combo uplift + BTC leg [HYPO][research_only].

Default split:
  train   2026-01-01 .. 2026-04-30
  holdout 2026-05-01 .. 2026-06-08  (May–Jun shock window)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.run_three_lens_horizon_empirical_eval_v1 as v1  # noqa: E402
from scripts.run_science_core_horizon_empirical_eval_v1 import (  # noqa: E402
    DEFAULT_SCIENCE_JSONL_BTC,
    DEFAULT_SCIENCE_JSONL_KOSPI,
    _ensure_science_jsonl,
    run_eval,
)
from scripts.run_science_core_kospi_combo_backtest_v1 import run_backtest  # noqa: E402

DEFAULT_OUT = ROOT / "reports/science_core_holdout_combo_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/science_core_holdout_combo_v1_latest.json"

DEFAULT_TRAIN_FROM = "2026-01-01"
DEFAULT_TRAIN_TO = "2026-04-30"
DEFAULT_HOLDOUT_FROM = "2026-05-01"
DEFAULT_HOLDOUT_TO = "2026-06-08"

COMBO_LENS_IDS = (
    "science_core",
    "science_plus_sasang",
    "science_plus_myeongni",
    "science_plus_logos",
)
HOLDOUT_REQUIRED_HORIZONS = ("short_1d", "mid_5d")
MIN_HOLDOUT_N = 10
MIN_UPLIFT_SOFT = 0.03


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _soft_at(matrix: dict[str, Any], lens_id: str, horizon: str) -> float | None:
    block = (matrix.get(lens_id) or {}).get(horizon) or {}
    v = block.get("soft_hit_rate")
    return float(v) if v is not None else None


def _best_combo_short(matrix: dict[str, Any]) -> dict[str, Any]:
    best_id = None
    best_soft = None
    for lid in COMBO_LENS_IDS:
        soft = _soft_at(matrix, lid, "short_1d")
        if soft is None:
            continue
        if best_soft is None or soft > best_soft:
            best_soft = soft
            best_id = lid
    science_soft = _soft_at(matrix, "science_core", "short_1d")
    uplift = round(best_soft - science_soft, 4) if best_soft is not None and science_soft is not None else None
    return {
        "best_lens_id": best_id,
        "best_short_1d_soft": best_soft,
        "science_core_short_1d_soft": science_soft,
        "uplift_vs_science_alone": uplift,
    }


def _attach_recommendation(train: dict[str, Any], holdout: dict[str, Any]) -> dict[str, Any]:
    h = _best_combo_short(holdout.get("rate_matrix") or {})
    t = _best_combo_short(train.get("rate_matrix") or {})
    uplift = h.get("uplift_vs_science_alone")
    best = h.get("best_lens_id")
    holdout_n = int((holdout.get("rate_matrix") or {}).get("science_core", {}).get("short_1d", {}).get("n_scored") or 0)
    recommended = (
        holdout_n >= MIN_HOLDOUT_N
        and uplift is not None
        and float(uplift) >= MIN_UPLIFT_SOFT
        and best is not None
        and best != "science_core"
    )
    return {
        "always_attach_recommended": recommended,
        "recommended_combo_lens_id": best if recommended else "science_core_only",
        "holdout_n_scored_short_1d": holdout_n,
        "min_holdout_n": MIN_HOLDOUT_N,
        "min_uplift_soft_threshold": MIN_UPLIFT_SOFT,
        "train_best_combo": t,
        "holdout_best_combo": h,
        "note": "Holdout uplift gate; not Track A promotion.",
    }


def run_holdout_bundle(
    *,
    train_from: str,
    train_to: str,
    holdout_from: str,
    holdout_to: str,
    neutral_bps: float,
    myeongni_jsonl: Path,
    sasang_jsonl: Path,
    logos_lens: Path,
    logos_jsonl: Path | None = None,
    rebuild_science: bool,
) -> dict[str, Any]:
    full_from = min(train_from, holdout_from)
    full_to = max(train_to, holdout_to)

    kospi_jsonl = DEFAULT_SCIENCE_JSONL_KOSPI
    btc_jsonl = DEFAULT_SCIENCE_JSONL_BTC
    from scripts.run_science_core_governance_bundle_v1 import _science_jsonl_needs_rebuild

    if rebuild_science or _science_jsonl_needs_rebuild(kospi_jsonl, full_from, full_to):
        _ensure_science_jsonl(
            instrument="kospi",
            csv_path=v1.KOSPI_CSV,
            out_path=kospi_jsonl,
            date_from=full_from,
            date_to=full_to,
            apply_overnight=True,
        )
    if rebuild_science or _science_jsonl_needs_rebuild(btc_jsonl, full_from, full_to):
        _ensure_science_jsonl(
            instrument="btc",
            csv_path=v1.BTC_CSV,
            out_path=btc_jsonl,
            date_from=full_from,
            date_to=full_to,
            apply_overnight=False,
        )

    eval_common = dict(
        neutral_bps=neutral_bps,
        myeongni_jsonl=myeongni_jsonl,
        sasang_jsonl=sasang_jsonl,
        logos_lens=logos_lens,
        logos_jsonl=logos_jsonl,
        myeongni_momentum_window=5,
    )
    backtest_common = dict(
        neutral_bps=neutral_bps,
        myeongni_jsonl=myeongni_jsonl,
        sasang_jsonl=sasang_jsonl,
        logos_lens=logos_lens,
        myeongni_momentum_window=5,
    )

    kospi_train = run_eval(
        instrument="kospi",
        csv_path=v1.KOSPI_CSV,
        science_jsonl=kospi_jsonl,
        date_from=train_from,
        date_to=train_to,
        **eval_common,
    )
    kospi_holdout = run_eval(
        instrument="kospi",
        csv_path=v1.KOSPI_CSV,
        science_jsonl=kospi_jsonl,
        date_from=holdout_from,
        date_to=holdout_to,
        required_horizons=HOLDOUT_REQUIRED_HORIZONS,
        **eval_common,
    )
    btc_train = run_eval(
        instrument="btc",
        csv_path=v1.BTC_CSV,
        science_jsonl=btc_jsonl,
        date_from=train_from,
        date_to=train_to,
        **eval_common,
    )
    btc_holdout = run_eval(
        instrument="btc",
        csv_path=v1.BTC_CSV,
        science_jsonl=btc_jsonl,
        date_from=holdout_from,
        date_to=holdout_to,
        required_horizons=HOLDOUT_REQUIRED_HORIZONS,
        **eval_common,
    )

    pnl_train = run_backtest(
        csv_path=v1.KOSPI_CSV,
        science_jsonl=kospi_jsonl,
        date_from=train_from,
        date_to=train_to,
        fee_bps=5.0,
        **backtest_common,
    )
    pnl_holdout = run_backtest(
        csv_path=v1.KOSPI_CSV,
        science_jsonl=kospi_jsonl,
        date_from=holdout_from,
        date_to=holdout_to,
        fee_bps=5.0,
        **backtest_common,
    )

    attach = _attach_recommendation(kospi_train, kospi_holdout)

    return {
        "schema": "science_core_holdout_combo_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "boundary_ack": True,
        "windows": {
            "train": {"from": train_from, "to": train_to},
            "holdout_shock": {"from": holdout_from, "to": holdout_to},
        },
        "kospi": {
            "horizon_train": kospi_train,
            "horizon_holdout": kospi_holdout,
            "pnl_backtest_train": pnl_train,
            "pnl_backtest_holdout": pnl_holdout,
            "attach_recommendation": attach,
        },
        "btc": {
            "horizon_train": btc_train,
            "horizon_holdout": btc_holdout,
        },
        "summary": {
            "kospi_holdout_best_combo": attach["holdout_best_combo"].get("best_lens_id"),
            "kospi_holdout_uplift_soft": attach["holdout_best_combo"].get("uplift_vs_science_alone"),
            "always_attach_recommended": attach["always_attach_recommended"],
            "recommended_combo": attach["recommended_combo_lens_id"],
            "kospi_train_n": kospi_train.get("n_eval_dates"),
            "kospi_holdout_n": kospi_holdout.get("n_eval_dates"),
            "btc_holdout_science_best": (btc_holdout.get("science_core_summary") or {}).get("best_horizon"),
        },
        "methodology_ko": (
            "Train/holdout 분리로 science 단독 vs 조합 uplift 판정. "
            "holdout=2026-05~06 shock. Track A·실매매 승격 근거 아님."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    from scripts.btrack_multilens_per_date_core_v1 import (  # noqa: E402
        DEFAULT_LOGOS_LENS,
        DEFAULT_MYEONGNI_JSONL,
        DEFAULT_SASANG_JSONL,
    )

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--train-from", type=str, default=DEFAULT_TRAIN_FROM)
    ap.add_argument("--train-to", type=str, default=DEFAULT_TRAIN_TO)
    ap.add_argument("--holdout-from", type=str, default=DEFAULT_HOLDOUT_FROM)
    ap.add_argument("--holdout-to", type=str, default=DEFAULT_HOLDOUT_TO)
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    ap.add_argument("--rebuild-science", action="store_true")
    ap.add_argument("--myeongni-jsonl", type=Path, default=DEFAULT_MYEONGNI_JSONL)
    ap.add_argument("--sasang-jsonl", type=Path, default=DEFAULT_SASANG_JSONL)
    ap.add_argument("--logos-lens", type=Path, default=DEFAULT_LOGOS_LENS)
    ap.add_argument("--logos-jsonl", type=Path, default=None)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact-output", type=Path, default=ART_OUT)
    args = ap.parse_args(argv)

    doc = run_holdout_bundle(
        train_from=args.train_from,
        train_to=args.train_to,
        holdout_from=args.holdout_from,
        holdout_to=args.holdout_to,
        neutral_bps=args.neutral_bps,
        myeongni_jsonl=args.myeongni_jsonl,
        sasang_jsonl=args.sasang_jsonl,
        logos_lens=args.logos_lens,
        logos_jsonl=args.logos_jsonl,
        rebuild_science=args.rebuild_science,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.artifact_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.artifact_output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    s = doc["summary"]
    print(
        f"WROTE: {args.output.resolve()} attach={s.get('always_attach_recommended')} "
        f"combo={s.get('recommended_combo')} uplift={s.get('kospi_holdout_uplift_soft')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
