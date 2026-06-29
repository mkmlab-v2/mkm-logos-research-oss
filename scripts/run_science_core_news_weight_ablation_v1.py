#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Science Core news/macro/price weight ablation [HYPO][research_only].

Re-blends stored per-date components — no EXA refetch. Holdout split matches humanist A/B.
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
    DEFAULT_MYEONGNI_JSONL,
    read_jsonl,
    row_asof,
    rows_by_calendar_day,
    score_sasang_at_date,
)
from scripts.btrack_science_core_v1 import (  # noqa: E402
    SCIENCE_WEIGHTS_DEFAULT,
    combo_direction_from_scores,
    recompose_science_from_components,
)
from scripts.run_science_core_horizon_empirical_eval_v1 import (  # noqa: E402
    COMBO_BLEND,
    DEFAULT_SCIENCE_JSONL_KOSPI,
    _build_labels_and_window,
    _science_component_direction,
)
import scripts.run_three_lens_horizon_empirical_eval_v1 as v1  # noqa: E402

DEFAULT_OUT = ROOT / "reports/science_core_news_weight_ablation_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/science_core_news_weight_ablation_v1_latest.json"
DEFAULT_MARKET_SASANG = ROOT / "reports/btrack_market_sasang_per_date_v1.jsonl"

WEIGHT_PROFILES: dict[str, dict[str, float]] = {
    "baseline_default": dict(SCIENCE_WEIGHTS_DEFAULT),
    "news_zero_renorm": {"price": 0.765, "macro": 0.235, "news": 0.0},
    "news_light_0.10": {"price": 0.60, "macro": 0.30, "news": 0.10},
    "news_heavy_0.25": {"price": 0.50, "macro": 0.25, "news": 0.25},
    "news_heavy_0.30": {"price": 0.45, "macro": 0.25, "news": 0.30},
    "macro_zero_renorm": {"price": 0.75, "macro": 0.0, "news": 0.25},
    "price_zero_renorm": {"price": 0.0, "macro": 0.50, "news": 0.50},
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _soft_hit_rate(outcomes: list[str]) -> dict[str, Any]:
    hits = sum(1 for o in outcomes if o == "HIT")
    fails = sum(1 for o in outcomes if o == "FAIL")
    neutral = sum(1 for o in outcomes if o == "NEUTRAL_DRAW")
    n = len(outcomes)
    n_dir = hits + fails
    return {
        "n_scored": n,
        "directional_hit_rate": round(hits / n_dir, 4) if n_dir else None,
        "soft_hit_rate": round((hits + 0.5 * neutral) / n, 4) if n else None,
    }


def _eval_profile(
    *,
    profile_id: str,
    weights: dict[str, float],
    science_by: dict[str, dict[str, Any]],
    window_days: list[str],
    labels: dict[str, dict[str, str]],
    sa_by: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    science_outcomes: list[str] = []
    combo_outcomes: list[str] = []
    component_only: dict[str, list[str]] = {"price_only": [], "macro_only": [], "news_only": []}

    for dk in window_days:
        if dk not in labels or "short_1d" not in labels[dk]:
            continue
        row = science_by.get(dk)
        actual = labels[dk]["short_1d"]
        if not row:
            continue

        _, science_dir = recompose_science_from_components(row, weights)
        science_outcomes.append(v1._outcome(science_dir, actual))

        sa_day, sa_asof = row_asof(sa_by, dk)
        sa = score_sasang_at_date(sa_asof, matched_day=sa_day, eval_date=dk)
        sa_score = float(sa.get("direction_score") or 0.0)
        sw, hw, _leg = COMBO_BLEND["science_plus_sasang"]
        combo_dir = combo_direction_from_scores(
            float(recompose_science_from_components(row, weights)[0]),
            sa_score,
            science_weight=sw,
            humanist_weight=hw,
        )
        combo_outcomes.append(v1._outcome(combo_dir, actual))

        for comp in component_only:
            component_only[comp].append(
                v1._outcome(_science_component_direction(row, comp.replace("_only", "")), actual)
            )

    return {
        "profile_id": profile_id,
        "weights": weights,
        "science_core_short_1d": _soft_hit_rate(science_outcomes),
        "science_plus_sasang_short_1d": _soft_hit_rate(combo_outcomes),
        "component_only_short_1d": {k: _soft_hit_rate(v) for k, v in component_only.items()},
    }


def run_ablation(
    *,
    science_jsonl: Path,
    sasang_jsonl: Path,
    myeongni_jsonl: Path,
    date_from: str,
    date_to: str,
    train_to: str,
    holdout_from: str,
    holdout_to: str,
    neutral_bps: float,
    profiles: dict[str, dict[str, float]] | None = None,
) -> dict[str, Any]:
    from scripts.run_three_lens_horizon_empirical_eval_v1 import KOSPI_CSV

    profiles = profiles or WEIGHT_PROFILES
    _, labels, window_days = _build_labels_and_window(
        KOSPI_CSV,
        date_from=date_from,
        date_to=date_to,
        neutral_bps=neutral_bps,
    )
    science_by: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(science_jsonl):
        dk = str(row.get("session_date") or "")[:10]
        if dk:
            science_by[dk] = row

    sa_by = rows_by_calendar_day(read_jsonl(sasang_jsonl))

    train_days = [d for d in window_days if d <= train_to]
    holdout_days = [d for d in window_days if holdout_from <= d <= holdout_to]

    arms: dict[str, Any] = {}
    for pid, weights in profiles.items():
        arms[pid] = {
            "train": _eval_profile(
                profile_id=pid,
                weights=weights,
                science_by=science_by,
                window_days=train_days,
                labels=labels,
                sa_by=sa_by,
            ),
            "holdout": _eval_profile(
                profile_id=pid,
                weights=weights,
                science_by=science_by,
                window_days=holdout_days,
                labels=labels,
                sa_by=sa_by,
            ),
        }

    baseline_hold = arms["baseline_default"]["holdout"]["science_plus_sasang_short_1d"]["soft_hit_rate"]
    ranked: list[dict[str, Any]] = []
    for pid, arm in arms.items():
        hold_soft = arm["holdout"]["science_plus_sasang_short_1d"]["soft_hit_rate"]
        ranked.append(
            {
                "profile_id": pid,
                "holdout_science_plus_sasang_soft": hold_soft,
                "delta_vs_baseline_soft": (
                    round(float(hold_soft) - float(baseline_hold), 4)
                    if hold_soft is not None and baseline_hold is not None
                    else None
                ),
            }
        )
    ranked.sort(key=lambda r: float(r.get("holdout_science_plus_sasang_soft") or 0.0), reverse=True)

    news_off_hold = arms["news_zero_renorm"]["holdout"]["science_plus_sasang_short_1d"]
    baseline_hold_combo = arms["baseline_default"]["holdout"]["science_plus_sasang_short_1d"]
    science_plus_sasang_news_off = {
        "weights": WEIGHT_PROFILES["news_zero_renorm"],
        "holdout_short_1d": news_off_hold,
        "delta_vs_baseline_combo_soft": (
            round(
                float(news_off_hold.get("soft_hit_rate") or 0)
                - float(baseline_hold_combo.get("soft_hit_rate") or 0),
                4,
            )
            if news_off_hold.get("soft_hit_rate") is not None
            else None
        ),
        "note_ko": "science leg news=0 renorm; sasang blend unchanged. Alias of news_zero_renorm combo arm.",
    }

    return {
        "schema": "science_core_news_weight_ablation_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "windows": {
            "full": {"from": date_from, "to": date_to},
            "train": {"from": date_from, "to": train_to},
            "holdout": {"from": holdout_from, "to": holdout_to},
        },
        "profiles": arms,
        "holdout_ranking_science_plus_sasang": ranked,
        "best_holdout_profile": ranked[0]["profile_id"] if ranked else None,
        "science_plus_sasang_news_off": science_plus_sasang_news_off,
        "verdict_ko": (
            "news 가중치 ablation은 stored component 재블렌드. holdout uplift만으로 Track A·실매매 승격 금지. "
            "news_zero가 baseline과 유사하면 news 레이어는 science+sasang uplift의 주원인이 아님."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--science-jsonl", type=Path, default=DEFAULT_SCIENCE_JSONL_KOSPI)
    ap.add_argument("--sasang-jsonl", type=Path, default=DEFAULT_MARKET_SASANG)
    ap.add_argument("--myeongni-jsonl", type=Path, default=DEFAULT_MYEONGNI_JSONL)
    ap.add_argument("--date-from", default="2026-01-01")
    ap.add_argument("--date-to", default="2026-06-08")
    ap.add_argument("--train-to", default="2026-04-30")
    ap.add_argument("--holdout-from", default="2026-05-01")
    ap.add_argument("--holdout-to", default="2026-06-08")
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact-output", type=Path, default=ART_OUT)
    args = ap.parse_args(argv)

    doc = run_ablation(
        science_jsonl=args.science_jsonl,
        sasang_jsonl=args.sasang_jsonl,
        myeongni_jsonl=args.myeongni_jsonl,
        date_from=args.date_from,
        date_to=args.date_to,
        train_to=args.train_to,
        holdout_from=args.holdout_from,
        holdout_to=args.holdout_to,
        neutral_bps=args.neutral_bps,
    )
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.artifact_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8")
    args.artifact_output.write_text(payload, encoding="utf-8")
    print(
        f"WROTE: {args.output.resolve()} best_holdout={doc.get('best_holdout_profile')} "
        f"baseline_holdout_soft="
        f"{doc['profiles']['baseline_default']['holdout']['science_plus_sasang_short_1d']['soft_hit_rate']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
