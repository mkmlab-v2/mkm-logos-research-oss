#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Long-window lane compare — pre-EXA vs EXA era [HYPO][research_only].

Includes science_plus_sasang_news_off (science leg with news weight 0, renorm price+macro).
Supports kospi and btc instruments.
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

from scripts.btrack_multilens_per_date_core_v1 import (  # noqa: E402
    DEFAULT_LOGOS_LENS,
    DEFAULT_MYEONGNI_JSONL,
    DEFAULT_SASANG_JSONL,
    read_jsonl,
    row_asof,
    rows_by_calendar_day,
    score_sasang_at_date,
)
from scripts.btrack_science_core_v1 import combo_direction_from_scores, recompose_science_from_components  # noqa: E402
from scripts.run_science_core_horizon_empirical_eval_v1 import (  # noqa: E402
    COMBO_BLEND,
    DEFAULT_SCIENCE_JSONL_BTC,
    DEFAULT_SCIENCE_JSONL_KOSPI,
    build_daily_short_rows,
)
from scripts.run_science_core_long_history_slice_eval_v1 import (  # noqa: E402
    _enrich_daily_rows,
    _outcome_rates,
    _rolling_vol_terciles,
)
import scripts.run_three_lens_horizon_empirical_eval_v1 as v1  # noqa: E402

DEFAULT_OUT = ROOT / "reports/science_core_long_window_lane_compare_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/science_core_long_window_lane_compare_v1_latest.json"
DEFAULT_OUT_BTC = ROOT / "reports/science_core_long_window_lane_compare_btc_v1_latest.json"
ART_OUT_BTC = ROOT / "docs/final/artifacts/science_core_long_window_lane_compare_btc_v1_latest.json"
DEFAULT_MARKET_SASANG = ROOT / "reports/btrack_market_sasang_per_date_v1.jsonl"
DEFAULT_MYEONGNI_PER_DATE = ROOT / "reports/btrack_myeongni_per_date_v1.jsonl"

NEWS_OFF_WEIGHTS = {"price": 0.765, "macro": 0.235, "news": 0.0}
COMPARE_LENS_IDS = (
    "science_core",
    "macro_only",
    "science_plus_sasang",
    "science_plus_myeongni",
    "science_plus_sasang_myeongni",
    "science_plus_sasang_news_off",
)

EXA_ERA_FROM = "2020-01-01"
EXA_ERA_TO = "2099-12-31"

INSTRUMENT_PROFILES: dict[str, dict[str, Any]] = {
    "kospi": {
        "csv": lambda: v1.KOSPI_CSV,
        "default_science_jsonl": DEFAULT_SCIENCE_JSONL_KOSPI,
        "pre_exa_era": ("1997-01-01", "2019-12-31"),
        "history_from": "1997-01-01",
        "default_out": DEFAULT_OUT,
        "default_art": ART_OUT,
    },
    "btc": {
        "csv": lambda: v1.BTC_CSV,
        "default_science_jsonl": DEFAULT_SCIENCE_JSONL_BTC,
        "pre_exa_era": ("2014-09-17", "2019-12-31"),
        "history_from": "2014-09-17",
        "default_out": DEFAULT_OUT_BTC,
        "default_art": ART_OUT_BTC,
    },
}

ERA_SLIM_KEYS = (
    "pre_exa_era",
    "exa_era_calendar_stub",
    "exa_era_market_sasang",
    "bundle_window_calendar_stub",
    "bundle_window_market_sasang",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _science_by_date(science_jsonl: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(science_jsonl):
        dk = str(row.get("session_date") or "")[:10]
        if dk:
            out[dk] = row
    return out


def _augment_news_off_outcomes(
    rows: list[dict[str, Any]],
    *,
    science_by: dict[str, dict[str, Any]],
    sa_by: dict[str, dict[str, Any]],
) -> None:
    sw, hw, _leg = COMBO_BLEND["science_plus_sasang"]
    for row in rows:
        dk = str(row.get("session_date") or "")[:10]
        science_row = science_by.get(dk)
        if not science_row or "actual_short_1d" not in row:
            continue
        sa_day, sa_asof = row_asof(sa_by, dk)
        sa = score_sasang_at_date(sa_asof, matched_day=sa_day, eval_date=dk)
        sa_score = float(sa.get("direction_score") or 0.0)
        sci_score, _ = recompose_science_from_components(science_row, NEWS_OFF_WEIGHTS)
        combo_dir = combo_direction_from_scores(
            sci_score, sa_score, science_weight=sw, humanist_weight=hw
        )
        outcomes = dict(row.get("outcomes_short_1d") or {})
        outcomes["science_plus_sasang_news_off"] = v1._outcome(combo_dir, row["actual_short_1d"])
        row["outcomes_short_1d"] = outcomes


def _slim_block(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"n_days": 0, "lenses": {}}
    lenses = {lid: _outcome_rates(rows, lid) for lid in COMPARE_LENS_IDS}
    ranked = sorted(
        [{"lens_id": lid, **m} for lid, m in lenses.items() if m.get("n_scored")],
        key=lambda x: float(x.get("soft_hit_rate") or -1.0),
        reverse=True,
    )
    macro_soft = (lenses.get("macro_only") or {}).get("soft_hit_rate")
    science_soft = (lenses.get("science_core") or {}).get("soft_hit_rate")
    combo_soft = (lenses.get("science_plus_sasang") or {}).get("soft_hit_rate")
    news_off_soft = (lenses.get("science_plus_sasang_news_off") or {}).get("soft_hit_rate")
    return {
        "n_days": len(rows),
        "date_min": min(str(r["session_date"]) for r in rows),
        "date_max": max(str(r["session_date"]) for r in rows),
        "best_lens_id": ranked[0]["lens_id"] if ranked else None,
        "lenses": lenses,
        "macro_only_not_recommended": bool(
            macro_soft is not None
            and science_soft is not None
            and float(macro_soft) > float(science_soft) + 0.05
            and ranked
            and ranked[0]["lens_id"] == "macro_only"
        ),
        "science_plus_sasang_news_off_delta_vs_combo": (
            round(float(news_off_soft) - float(combo_soft), 4)
            if news_off_soft is not None and combo_soft is not None
            else None
        ),
    }


def slim_eras_from_compare_doc(full: dict[str, Any]) -> dict[str, Any]:
    eras = full.get("eras") or {}
    slim: dict[str, Any] = {}
    for key in ERA_SLIM_KEYS:
        era = eras.get(key) or {}
        lenses = era.get("lenses") or {}
        slim[key] = {
            "n_days": era.get("n_days"),
            "best_lens_id": era.get("best_lens_id"),
            "macro_only_not_recommended": era.get("macro_only_not_recommended"),
            "science_core_soft": (lenses.get("science_core") or {}).get("soft_hit_rate"),
            "macro_only_soft": (lenses.get("macro_only") or {}).get("soft_hit_rate"),
            "science_plus_sasang_soft": (lenses.get("science_plus_sasang") or {}).get("soft_hit_rate"),
            "science_plus_myeongni_soft": (lenses.get("science_plus_myeongni") or {}).get("soft_hit_rate"),
            "science_plus_sasang_myeongni_soft": (
                (lenses.get("science_plus_sasang_myeongni") or {}).get("soft_hit_rate")
            ),
            "science_plus_sasang_news_off_soft": (
                (lenses.get("science_plus_sasang_news_off") or {}).get("soft_hit_rate")
            ),
            "news_off_delta_vs_combo": era.get("science_plus_sasang_news_off_delta_vs_combo"),
            "sasang_source": era.get("sasang_source"),
        }
    return slim


def _eval_era(
    *,
    era_id: str,
    era_from: str,
    era_to: str,
    clip_to: str,
    csv_path: Path,
    science_jsonl: Path,
    sasang_jsonl: Path,
    sasang_source: str,
    myeongni_jsonl: Path,
    myeongni_source: str,
    neutral_bps: float,
) -> dict[str, Any]:
    date_to = era_to if era_to <= clip_to else clip_to
    if date_to < era_from:
        return {
            "era_id": era_id,
            "n_days": 0,
            "skipped": True,
            "sasang_source": sasang_source,
            "myeongni_source": myeongni_source,
        }

    closes = v1._load_closes(csv_path)
    vol_tercile = _rolling_vol_terciles(closes, sorted(closes.keys()))
    daily = build_daily_short_rows(
        csv_path=csv_path,
        science_jsonl=science_jsonl,
        date_from=era_from,
        date_to=date_to,
        neutral_bps=neutral_bps,
        myeongni_jsonl=myeongni_jsonl,
        sasang_jsonl=sasang_jsonl,
        logos_lens=DEFAULT_LOGOS_LENS,
        logos_jsonl=None,
        myeongni_momentum_window=5,
    )
    science_by = _science_by_date(science_jsonl)
    sa_by = rows_by_calendar_day(read_jsonl(sasang_jsonl))
    _augment_news_off_outcomes(daily, science_by=science_by, sa_by=sa_by)
    rows = _enrich_daily_rows(daily, science_jsonl=science_jsonl, vol_tercile_by_day=vol_tercile)
    block = _slim_block(rows)
    block["era_id"] = era_id
    block["sasang_source"] = sasang_source
    block["myeongni_source"] = myeongni_source
    block["window"] = {"from": era_from, "to": date_to}
    return block


def run_compare(
    *,
    instrument: str,
    science_jsonl: Path,
    date_to: str,
    bundle_from: str,
    bundle_to: str,
    neutral_bps: float,
) -> dict[str, Any]:
    profile = INSTRUMENT_PROFILES[instrument]
    csv_path = profile["csv"]()
    pre_from, pre_to = profile["pre_exa_era"]
    eras: dict[str, Any] = {}
    myeongni_per_date = (
        DEFAULT_MYEONGNI_PER_DATE if DEFAULT_MYEONGNI_PER_DATE.is_file() else DEFAULT_MYEONGNI_JSONL
    )
    myeongni_per_date_source = (
        "manseryeok_per_date" if DEFAULT_MYEONGNI_PER_DATE.is_file() else "calendar_stub"
    )

    def _era(
        era_id: str,
        era_from: str,
        era_to: str,
        clip: str,
        sasang_jsonl: Path,
        sasang_source: str,
        myeongni_jsonl: Path,
        myeongni_source: str,
    ) -> dict[str, Any]:
        return _eval_era(
            era_id=era_id,
            era_from=era_from,
            era_to=era_to,
            clip_to=clip,
            csv_path=csv_path,
            science_jsonl=science_jsonl,
            sasang_jsonl=sasang_jsonl,
            sasang_source=sasang_source,
            myeongni_jsonl=myeongni_jsonl,
            myeongni_source=myeongni_source,
            neutral_bps=neutral_bps,
        )

    eras["pre_exa_era"] = _era(
        "pre_exa_era",
        pre_from,
        pre_to,
        date_to,
        DEFAULT_SASANG_JSONL,
        "calendar_stub",
        DEFAULT_MYEONGNI_JSONL,
        "calendar_stub",
    )
    eras["exa_era_calendar_stub"] = _era(
        "exa_era_calendar_stub",
        EXA_ERA_FROM,
        EXA_ERA_TO,
        date_to,
        DEFAULT_SASANG_JSONL,
        "calendar_stub",
        DEFAULT_MYEONGNI_JSONL,
        "calendar_stub",
    )
    eras["exa_era_market_sasang"] = _era(
        "exa_era_market_sasang",
        EXA_ERA_FROM,
        EXA_ERA_TO,
        date_to,
        DEFAULT_MARKET_SASANG,
        "market_psych_v2_per_date",
        myeongni_per_date,
        myeongni_per_date_source,
    )
    eras["bundle_window_calendar_stub"] = _era(
        "bundle_window_calendar_stub",
        bundle_from,
        bundle_to,
        bundle_to,
        DEFAULT_SASANG_JSONL,
        "calendar_stub",
        DEFAULT_MYEONGNI_JSONL,
        "calendar_stub",
    )
    eras["bundle_window_market_sasang"] = _era(
        "bundle_window_market_sasang",
        bundle_from,
        bundle_to,
        bundle_to,
        DEFAULT_MARKET_SASANG,
        "market_psych_v2_per_date",
        myeongni_per_date,
        myeongni_per_date_source,
    )

    return {
        "schema": "science_core_long_window_lane_compare_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "instrument": instrument,
        "eras": eras,
        "verdict_ko": (
            "pre_exa_era에서 macro_only 1위는 장기 in-sample bias와 동일 선상 — 전략 레인 금지. "
            "bundle_window는 market_sasang 필수; news_off는 combo 대비 holdout 미세 변화 기대. "
            "1997-2019 stored EXA 없음 — pre_exa는 price+macro·news_off 정책. Track A·실매매 승격 근거 아님."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--instrument", choices=tuple(INSTRUMENT_PROFILES), default="kospi")
    ap.add_argument("--science-jsonl", type=Path, default=None)
    ap.add_argument("--date-to", default="2026-06-08")
    ap.add_argument("--bundle-from", default="2026-01-01")
    ap.add_argument("--bundle-to", default="2026-06-08")
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    ap.add_argument("--output", type=Path, default=None)
    ap.add_argument("--artifact-output", type=Path, default=None)
    args = ap.parse_args(argv)

    profile = INSTRUMENT_PROFILES[args.instrument]
    science_jsonl = args.science_jsonl or profile["default_science_jsonl"]
    out_path = args.output or profile["default_out"]
    art_path = args.artifact_output or profile["default_art"]

    doc = run_compare(
        instrument=args.instrument,
        science_jsonl=science_jsonl,
        date_to=args.date_to,
        bundle_from=args.bundle_from,
        bundle_to=args.bundle_to,
        neutral_bps=args.neutral_bps,
    )
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    art_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(payload, encoding="utf-8")
    art_path.write_text(payload, encoding="utf-8")
    pre = doc["eras"].get("pre_exa_era") or {}
    print(
        f"WROTE: {out_path.resolve()} instrument={args.instrument} pre_exa_best={pre.get('best_lens_id')} "
        f"bundle_market_combo="
        f"{(doc['eras'].get('bundle_window_market_sasang') or {}).get('lenses', {}).get('science_plus_sasang', {}).get('soft_hit_rate')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
