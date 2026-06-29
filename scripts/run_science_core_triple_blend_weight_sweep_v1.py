#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""3-way science+sasang+myeongni weight sweep on holdout [HYPO][research_only]."""
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
    causal_rows_through,
    read_jsonl,
    row_asof,
    rows_by_calendar_day,
    score_myeongni_at_date,
    score_sasang_at_date,
)
from scripts.btrack_science_core_v1 import (  # noqa: E402
    TRIPLE_BLEND_WEIGHTS,
    combo_direction_from_scores,
    direction_from_score,
)
from scripts.run_science_core_horizon_empirical_eval_v1 import (  # noqa: E402
    COMBO_BLEND,
    DEFAULT_SCIENCE_JSONL_KOSPI,
    _build_labels_and_window,
)
import scripts.run_three_lens_horizon_empirical_eval_v1 as v1  # noqa: E402

DEFAULT_OUT = ROOT / "reports/science_core_triple_blend_weight_sweep_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/science_core_triple_blend_weight_sweep_v1_latest.json"
DEFAULT_MARKET_SASANG = ROOT / "reports/btrack_market_sasang_per_date_v1.jsonl"
DEFAULT_MYEONGNI_PER_DATE = ROOT / "reports/btrack_myeongni_per_date_v1.jsonl"

DEFAULT_TRAIN_TO = "2026-04-30"
DEFAULT_HOLDOUT_FROM = "2026-05-01"
DEFAULT_HOLDOUT_TO = "2026-06-08"


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


def _triple_dir(science_score: float, sa_score: float, my_score: float, weights: dict[str, float]) -> str:
    blended = (
        weights["science"] * science_score
        + weights["sasang"] * sa_score
        + weights["myeongni"] * my_score
    )
    return direction_from_score(blended)


def _default_weight_grid() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for science_w in (0.40, 0.45, 0.50, 0.55, 0.60):
        humanist_w = round(1.0 - science_w, 4)
        for sasang_share in (0.5, 0.6, 0.7, 0.8, 1.0):
            sasang_w = round(humanist_w * sasang_share, 4)
            myeongni_w = round(humanist_w - sasang_w, 4)
            if myeongni_w < 0:
                continue
            pid = f"sci{int(science_w * 100)}_sa{int(sasang_share * 100)}"
            rows.append(
                {
                    "profile_id": pid,
                    "weights": {
                        "science": science_w,
                        "sasang": sasang_w,
                        "myeongni": myeongni_w,
                    },
                }
            )
    baseline = dict(TRIPLE_BLEND_WEIGHTS)
    rows.insert(
        0,
        {
            "profile_id": "baseline_50_25_25",
            "weights": baseline,
        },
    )
    return rows


def _eval_window(
    *,
    profile_id: str,
    weights: dict[str, float],
    science_by: dict[str, dict[str, Any]],
    window_days: list[str],
    labels: dict[str, dict[str, str]],
    sa_by: dict[str, dict[str, Any]],
    my_by: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    triple_outcomes: list[str] = []
    sasang_combo_outcomes: list[str] = []
    sw, hw, _leg = COMBO_BLEND["science_plus_sasang"]

    for dk in window_days:
        if dk not in labels or "short_1d" not in labels[dk]:
            continue
        row = science_by.get(dk)
        if not row:
            continue
        actual = labels[dk]["short_1d"]
        science_score = float((row.get("scores") or {}).get("direction_score") or 0.0)
        sa_day, sa_asof = row_asof(sa_by, dk)
        my_day, _ = row_asof(my_by, dk)
        sa = score_sasang_at_date(sa_asof, matched_day=sa_day, eval_date=dk)
        my_hist = causal_rows_through(my_by, dk)
        my = score_myeongni_at_date(my_hist, eval_date=dk, matched_day=my_day, momentum_window=5)
        sa_score = float(sa.get("direction_score") or 0.0)
        my_score = float(my.get("direction_score") or 0.0)
        triple_outcomes.append(
            v1._outcome(_triple_dir(science_score, sa_score, my_score, weights), actual)
        )
        sasang_combo_outcomes.append(
            v1._outcome(
                combo_direction_from_scores(science_score, sa_score, science_weight=sw, humanist_weight=hw),
                actual,
            )
        )

    triple = _soft_hit_rate(triple_outcomes)
    sasang_combo = _soft_hit_rate(sasang_combo_outcomes)
    t_soft = triple.get("soft_hit_rate")
    s_soft = sasang_combo.get("soft_hit_rate")
    return {
        "profile_id": profile_id,
        "weights": weights,
        "triple_short_1d": triple,
        "science_plus_sasang_short_1d": sasang_combo,
        "triple_minus_sasang_combo_soft": (
            round(float(t_soft) - float(s_soft), 4) if t_soft is not None and s_soft is not None else None
        ),
    }


def run_sweep(
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
    profiles: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    from scripts.run_three_lens_horizon_empirical_eval_v1 import KOSPI_CSV

    profiles = profiles or _default_weight_grid()
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
    my_by = rows_by_calendar_day(read_jsonl(myeongni_jsonl))
    holdout_days = [d for d in window_days if holdout_from <= d <= holdout_to]
    train_days = [d for d in window_days if d <= train_to]

    arms: list[dict[str, Any]] = []
    for prof in profiles:
        pid = str(prof["profile_id"])
        weights = prof["weights"]
        arms.append(
            {
                "train": _eval_window(
                    profile_id=pid,
                    weights=weights,
                    science_by=science_by,
                    window_days=train_days,
                    labels=labels,
                    sa_by=sa_by,
                    my_by=my_by,
                ),
                "holdout": _eval_window(
                    profile_id=pid,
                    weights=weights,
                    science_by=science_by,
                    window_days=holdout_days,
                    labels=labels,
                    sa_by=sa_by,
                    my_by=my_by,
                ),
            }
        )

    ranked = sorted(
        [
            {
                "profile_id": a["holdout"]["profile_id"],
                "weights": a["holdout"]["weights"],
                "holdout_triple_soft": a["holdout"]["triple_short_1d"].get("soft_hit_rate"),
                "holdout_sasang_combo_soft": a["holdout"]["science_plus_sasang_short_1d"].get("soft_hit_rate"),
                "triple_minus_sasang_combo_soft": a["holdout"].get("triple_minus_sasang_combo_soft"),
            }
            for a in arms
        ],
        key=lambda r: float(r.get("holdout_triple_soft") or -1.0),
        reverse=True,
    )
    baseline_hold = next(
        (a["holdout"] for a in arms if a["holdout"]["profile_id"] == "baseline_50_25_25"),
        arms[0]["holdout"] if arms else {},
    )
    best = ranked[0] if ranked else None
    sasang_ref = baseline_hold.get("science_plus_sasang_short_1d", {}).get("soft_hit_rate")

    return {
        "schema": "science_core_triple_blend_weight_sweep_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "windows": {
            "full": {"from": date_from, "to": date_to},
            "train": {"from": date_from, "to": train_to},
            "holdout": {"from": holdout_from, "to": holdout_to},
        },
        "inputs": {
            "science_jsonl": str(science_jsonl),
            "sasang_jsonl": str(sasang_jsonl),
            "myeongni_jsonl": str(myeongni_jsonl),
        },
        "baseline_holdout": baseline_hold,
        "holdout_sasang_combo_reference_soft": sasang_ref,
        "best_holdout_triple": best,
        "any_triple_beats_sasang_combo_on_holdout": any(
            (r.get("triple_minus_sasang_combo_soft") or 0) > 0 for r in ranked
        ),
        "ranked_holdout_by_triple_soft": ranked[:10],
        "arms": {a["holdout"]["profile_id"]: a for a in arms},
        "verdict_ko": (
            "3-way 가중치 스윕은 sasang 2-way 대비 열세면 attach 레인 변경 근거 없음. "
            "Track A·실매매 승격 아님."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date-from", default="2026-01-01")
    ap.add_argument("--date-to", default="2026-06-08")
    ap.add_argument("--train-to", default=DEFAULT_TRAIN_TO)
    ap.add_argument("--holdout-from", default=DEFAULT_HOLDOUT_FROM)
    ap.add_argument("--holdout-to", default=DEFAULT_HOLDOUT_TO)
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    ap.add_argument("--science-jsonl", type=Path, default=DEFAULT_SCIENCE_JSONL_KOSPI)
    ap.add_argument("--sasang-jsonl", type=Path, default=DEFAULT_MARKET_SASANG)
    ap.add_argument("--myeongni-jsonl", type=Path, default=None)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact-output", type=Path, default=ART_OUT)
    args = ap.parse_args(argv)

    myeongni = args.myeongni_jsonl
    if myeongni is None:
        myeongni = DEFAULT_MYEONGNI_PER_DATE if DEFAULT_MYEONGNI_PER_DATE.is_file() else DEFAULT_MYEONGNI_JSONL

    doc = run_sweep(
        science_jsonl=args.science_jsonl,
        sasang_jsonl=args.sasang_jsonl,
        myeongni_jsonl=myeongni,
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
    best = doc.get("best_holdout_triple") or {}
    print(
        f"WROTE: {args.output.resolve()} best_triple={best.get('profile_id')} "
        f"soft={best.get('holdout_triple_soft')} beats_sasang={doc.get('any_triple_beats_sasang_combo_on_holdout')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
