#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Macro risk gate in-sample / persistence bias audit [HYPO][research_only]."""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.run_three_lens_horizon_empirical_eval_v1 as v1  # noqa: E402
from scripts.run_science_core_horizon_empirical_eval_v1 import (  # noqa: E402
    DEFAULT_SCIENCE_JSONL_KOSPI,
    _predictions_for_date,
    _science_component_direction,
)
from scripts.btrack_multilens_per_date_core_v1 import (  # noqa: E402
    DEFAULT_LOGOS_LENS,
    DEFAULT_MYEONGNI_JSONL,
    DEFAULT_SASANG_JSONL,
    read_jsonl,
    rows_by_calendar_day,
)

DEFAULT_OUT = ROOT / "reports/science_core_macro_gate_bias_audit_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/science_core_macro_gate_bias_audit_v1_latest.json"

HORIZONS = ("short_1d", "mid_5d", "macro_21d")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _outcome(pred: str, actual: str) -> str:
    return v1._outcome(pred, actual)


def _hit_rate(preds: list[str], actuals: list[str]) -> dict[str, Any]:
    rows = [_outcome(p, a) for p, a in zip(preds, actuals)]
    hits = sum(1 for o in rows if o == "HIT")
    fails = sum(1 for o in rows if o == "FAIL")
    neutral = sum(1 for o in rows if o == "NEUTRAL_DRAW")
    n = len(rows)
    n_dir = hits + fails
    return {
        "n_scored": n,
        "directional_hit_rate": round(hits / n_dir, 4) if n_dir else None,
        "soft_hit_rate": round((hits + 0.5 * neutral) / n, 4) if n else None,
    }


def _trailing_return_sign(
    closes: dict[str, float],
    trading_days: list[str],
    idx: int,
    *,
    window: int,
    neutral_bps: float,
) -> str | None:
    if idx < window:
        return None
    d0 = trading_days[idx - window]
    d1 = trading_days[idx]
    c0, c1 = closes.get(d0), closes.get(d1)
    if c0 is None or c1 is None or c0 == 0:
        return None
    ret = (c1 - c0) / c0
    return v1._direction_from_return(ret, neutral_bps)


def run_audit(
    *,
    csv_path: Path,
    science_jsonl: Path,
    date_from: str | None,
    date_to: str | None,
    neutral_bps: float,
    shuffle_trials: int,
    seed: int,
) -> dict[str, Any]:
    closes = v1._load_closes(csv_path)
    trading_days = sorted(closes.keys())
    science_by: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(science_jsonl):
        dk = str(row.get("session_date") or "")[:10]
        if dk:
            science_by[dk] = row

    window_days = trading_days
    if date_from:
        window_days = [d for d in window_days if d >= date_from]
    if date_to:
        window_days = [d for d in window_days if d <= date_to]

    labels: dict[str, dict[str, str]] = {}
    for i, dk in enumerate(trading_days):
        if dk not in window_days:
            continue
        row_labels: dict[str, str] = {}
        for hname, hdays in {"short_1d": 1, "mid_5d": 5, "macro_21d": 21}.items():
            fr = v1._forward_return(closes, trading_days, i, hdays)
            if fr is not None:
                row_labels[hname] = v1._direction_from_return(fr, neutral_bps)
        if row_labels:
            labels[dk] = row_labels

    macro_preds: list[str] = []
    science_preds: list[str] = []
    actual_short: list[str] = []
    actual_macro21: list[str] = []
    trailing21_sign: list[str] = []
    macro_scores: list[float] = []
    dates: list[str] = []
    myeongni_by_day = rows_by_calendar_day(read_jsonl(DEFAULT_MYEONGNI_JSONL))
    sasang_by_day = rows_by_calendar_day(read_jsonl(DEFAULT_SASANG_JSONL))

    for dk in window_days:
        if dk not in labels or "short_1d" not in labels[dk] or "macro_21d" not in labels[dk]:
            continue
        idx = trading_days.index(dk)
        science_row = science_by.get(dk)
        if not science_row:
            continue
        macro_pred = _science_component_direction(science_row, "macro")
        science_pred = _predictions_for_date(
            dk,
            science_row=science_row,
            myeongni_by_day=myeongni_by_day,
            sasang_by_day=sasang_by_day,
            logos_block={"direction": "neutral", "non_gating": True},
            myeongni_momentum_window=5,
        ).get("science_core", "neutral")
        trail = _trailing_return_sign(closes, trading_days, idx, window=21, neutral_bps=neutral_bps)
        if trail is None:
            continue
        macro_block = (science_row.get("components") or {}).get("macro") or {}
        score = float(macro_block.get("direction_score") or 0.0)
        dates.append(dk)
        macro_preds.append(macro_pred)
        science_preds.append(science_pred)
        actual_short.append(labels[dk]["short_1d"])
        actual_macro21.append(labels[dk]["macro_21d"])
        trailing21_sign.append(trail)
        macro_scores.append(score)

    n = len(dates)
    flips = sum(1 for i in range(1, n) if macro_preds[i] != macro_preds[i - 1])
    score_buckets = Counter(round(s, 2) for s in macro_scores)
    trail_agree_macro21 = sum(
        1 for m, t, a in zip(macro_preds, trailing21_sign, actual_macro21)
        if m not in ("neutral",) and t == m
    )
    trail_agree_macro21_rate = round(trail_agree_macro21 / n, 4) if n else None

    rng = random.Random(seed)
    shuffle_hits_short: list[float] = []
    shuffle_hits_macro21: list[float] = []
    for _ in range(max(0, shuffle_trials)):
        shuffled = macro_preds[:]
        rng.shuffle(shuffled)
        shuffle_hits_short.append(
            float(_hit_rate(shuffled, actual_short).get("directional_hit_rate") or 0.0)
        )
        shuffle_hits_macro21.append(
            float(_hit_rate(shuffled, actual_macro21).get("directional_hit_rate") or 0.0)
        )

    observed_short = _hit_rate(macro_preds, actual_short)
    observed_macro21 = _hit_rate(macro_preds, actual_macro21)
    observed_trail21_proxy = _hit_rate(trailing21_sign, actual_macro21)
    science_short = _hit_rate(science_preds, actual_short)

    shuffle_short_mean = round(sum(shuffle_hits_short) / len(shuffle_hits_short), 4) if shuffle_hits_short else None
    shuffle_macro21_mean = round(sum(shuffle_hits_macro21) / len(shuffle_hits_macro21), 4) if shuffle_hits_macro21 else None

    macro21_hit = float(observed_macro21.get("directional_hit_rate") or 0.0)
    bias_flags: list[str] = []
    if n and Counter(macro_preds).most_common(1)[0][1] / n >= 0.85:
        bias_flags.append("sticky_macro_direction")
    if macro21_hit >= 0.65 and shuffle_macro21_mean is not None and macro21_hit - shuffle_macro21_mean >= 0.15:
        bias_flags.append("macro21_hit_above_shuffle_margin")
    if trail_agree_macro21_rate is not None and trail_agree_macro21_rate >= 0.55:
        bias_flags.append("macro_aligns_with_trailing21d_sign")
    if len(score_buckets) <= 3:
        bias_flags.append("low_macro_score_entropy")

    return {
        "schema": "science_core_macro_gate_bias_audit_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "boundary_ack": True,
        "instrument": "kospi",
        "csv_path": str(csv_path).replace("\\", "/"),
        "science_jsonl": str(science_jsonl).replace("\\", "/"),
        "date_from": date_from,
        "date_to": date_to,
        "neutral_bps": neutral_bps,
        "n_eval_days": n,
        "macro_score_buckets": dict(score_buckets),
        "macro_direction_counts": dict(Counter(macro_preds)),
        "persistence": {
            "flip_count": flips,
            "flip_rate": round(flips / (n - 1), 4) if n > 1 else None,
            "sticky_regime_suspect": bool(n and Counter(macro_preds).most_common(1)[0][1] / n >= 0.85),
        },
        "observed_hit_rates": {
            "macro_only_vs_short_1d": observed_short,
            "macro_only_vs_macro_21d": observed_macro21,
            "trailing21d_sign_vs_macro_21d_label": observed_trail21_proxy,
            "science_core_vs_short_1d": science_short,
        },
        "trailing21_agreement": {
            "macro_pred_equals_trailing21d_sign_rate": trail_agree_macro21_rate,
            "note": "높으면 macro 게이트가 과거 21일 수익 부호와 정렬 — macro_21d 라벨과 동행 가능(in-sample 의심).",
        },
        "shuffle_null": {
            "trials": shuffle_trials,
            "seed": seed,
            "macro_only_vs_short_1d_mean_directional_hit": shuffle_short_mean,
            "macro_only_vs_macro_21d_mean_directional_hit": shuffle_macro21_mean,
        },
        "bias_flags": bias_flags,
        "verdict_ko": (
            "macro_only 장기 고적중은 shuffle 대비 유의하면 in-sample/동행 라벨 의심. "
            "Track A·일별 실전 근거로 사용 금지."
        ),
        "promotion_gate": {
            "track_a_ready": False,
            "live_trading_ready": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date-from", type=str, default="1997-01-01")
    ap.add_argument("--date-to", type=str, default="2026-06-08")
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    ap.add_argument("--science-jsonl", type=Path, default=DEFAULT_SCIENCE_JSONL_KOSPI)
    ap.add_argument("--shuffle-trials", type=int, default=200)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact-output", type=Path, default=ART_OUT)
    args = ap.parse_args(argv)

    if not args.science_jsonl.is_file():
        print(f"ERROR: missing {args.science_jsonl}", file=sys.stderr)
        return 1

    doc = run_audit(
        csv_path=v1.KOSPI_CSV,
        science_jsonl=args.science_jsonl,
        date_from=args.date_from,
        date_to=args.date_to,
        neutral_bps=args.neutral_bps,
        shuffle_trials=args.shuffle_trials,
        seed=args.seed,
    )
    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.artifact_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    args.artifact_output.write_text(text, encoding="utf-8")
    flags = ",".join(doc.get("bias_flags") or []) or "none"
    m21 = (doc.get("observed_hit_rates") or {}).get("macro_only_vs_macro_21d") or {}
    print(
        f"WROTE: {args.output.resolve()} n={doc.get('n_eval_days')} "
        f"macro21_hit={m21.get('directional_hit_rate')} flags={flags}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
