#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Science Core horizon eval + humanist combo grid [HYPO][research_only].

Measures science_core_v1 alone and pairwise combos:
  science_plus_sasang | science_plus_myeongni | science_plus_logos (advisory blend)
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
    causal_rows_through,
    logos_global,
    read_jsonl,
    row_asof,
    rows_by_calendar_day,
    score_myeongni_at_date,
    score_sasang_at_date,
    sign_to_dir,
)
from scripts.btrack_logos_per_date_core_v1 import (  # noqa: E402
    DEFAULT_LOGOS_PER_DATE_JSONL,
    logos_block_at_date,
    read_logos_per_date_jsonl,
)
from scripts.btrack_science_core_v1 import (  # noqa: E402
    combo_direction_from_scores,
    direction_from_score,
    triple_sasang_myeongni_direction,
)
import scripts.run_three_lens_horizon_empirical_eval_v1 as v1  # noqa: E402

def _repo_rel(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


DEFAULT_SCIENCE_JSONL_KOSPI = ROOT / "reports/btrack_science_core_per_date_kospi_v1.jsonl"
DEFAULT_SCIENCE_JSONL_BTC = ROOT / "reports/btrack_science_core_per_date_btc_v1.jsonl"
DEFAULT_SCIENCE_JSONL = DEFAULT_SCIENCE_JSONL_KOSPI  # legacy alias
DEFAULT_OUT = ROOT / "reports/science_core_horizon_empirical_eval_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/science_core_horizon_empirical_eval_v1_latest.json"

REQUIRED_HORIZONS = ("short_1d", "mid_10d", "macro_21d")

HORIZONS: dict[str, int] = {
    **v1.HORIZONS,
    "mid_5d": 5,
    "mid_15d": 15,
}

ROLE_MATCHED_HORIZON: dict[str, str] = {
    "science_core": "mid_5d",
    "science_plus_sasang": "short_1d",
    "science_plus_myeongni": "mid_10d",
    "science_plus_logos": "macro_21d",
    "science_plus_sasang_myeongni": "short_1d",
    "price_only": "short_1d",
    "macro_only": "macro_21d",
    "news_only": "short_1d",
}

COMBO_BLEND: dict[str, tuple[float, float, str]] = {
    "science_plus_sasang": (0.55, 0.45, "sasang"),
    "science_plus_myeongni": (0.55, 0.45, "myeongni"),
    "science_plus_logos": (0.70, 0.30, "logos"),
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_science_by_date(path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(path):
        dk = str(row.get("session_date") or "")[:10]
        if dk:
            out[dk] = row
    return out


def _science_component_direction(row: dict[str, Any], component: str) -> str:
    comps = row.get("components") if isinstance(row.get("components"), dict) else {}
    block = comps.get(component) if isinstance(comps.get(component), dict) else {}
    score = float(block.get("direction_score") or 0.0)
    return direction_from_score(score)


def _predictions_for_date(
    dk: str,
    *,
    science_row: dict[str, Any] | None,
    myeongni_by_day: dict[str, dict[str, Any]],
    sasang_by_day: dict[str, dict[str, Any]],
    logos_block: dict[str, Any],
    myeongni_momentum_window: int,
) -> dict[str, str]:
    preds: dict[str, str] = {}
    if not science_row:
        science_score = 0.0
        science_dir = "neutral"
        preds["price_only"] = "neutral"
        preds["macro_only"] = "neutral"
        preds["news_only"] = "neutral"
    else:
        science_score = float((science_row.get("scores") or {}).get("direction_score") or 0.0)
        science_dir = str(science_row.get("direction") or direction_from_score(science_score))
        preds["science_core"] = science_dir
        preds["price_only"] = _science_component_direction(science_row, "price")
        preds["macro_only"] = _science_component_direction(science_row, "macro")
        preds["news_only"] = _science_component_direction(science_row, "news")

    my_day, _ = row_asof(myeongni_by_day, dk)
    sa_day, sa_asof = row_asof(sasang_by_day, dk)
    my_hist = causal_rows_through(myeongni_by_day, dk)
    my = score_myeongni_at_date(
        my_hist, eval_date=dk, matched_day=my_day, momentum_window=myeongni_momentum_window
    )
    sa = score_sasang_at_date(sa_asof, matched_day=sa_day, eval_date=dk)
    my_score = float(my.get("direction_score") or 0.0)
    sa_score = float(sa.get("direction_score") or 0.0)
    logos_sign = int(logos_block.get("sign") or 0)
    logos_score = float(logos_block.get("direction_score") or 0.0) if logos_block.get("direction_score") is not None else float(logos_sign) * 0.55

    humanist = {
        "sasang": v1._score_to_direction(sa_score),
        "myeongni": v1._score_to_direction(my_score),
        "logos": sign_to_dir(logos_sign),
    }

    if science_row:
        preds["science_core"] = science_dir
        for combo_id, (sw, hw, leg) in COMBO_BLEND.items():
            leg_score = sa_score if leg == "sasang" else my_score if leg == "myeongni" else logos_score
            preds[combo_id] = combo_direction_from_scores(science_score, leg_score, science_weight=sw, humanist_weight=hw)
        preds["science_plus_sasang_myeongni"] = triple_sasang_myeongni_direction(
            science_score, sa_score, my_score
        )

    preds["sasang"] = humanist["sasang"]
    preds["myeongni"] = humanist["myeongni"]
    preds["logos_humanist"] = humanist["logos"]

    return preds


def _rate_matrix(scored: list[dict[str, Any]], lens_ids: list[str]) -> dict[str, dict[str, dict[str, float | int | None]]]:
    out: dict[str, dict[str, dict[str, float | int | None]]] = {}
    for lens_id in lens_ids:
        out[lens_id] = {}
        for hname in HORIZONS:
            rows = [r for r in scored if r.get("lens_id") == lens_id and r.get("horizon") == hname]
            hits = sum(1 for r in rows if r.get("outcome") == "HIT")
            fails = sum(1 for r in rows if r.get("outcome") == "FAIL")
            neutral = sum(1 for r in rows if r.get("outcome") == "NEUTRAL_DRAW")
            n = len(rows)
            n_dir = hits + fails
            out[lens_id][hname] = {
                "n_scored": n,
                "hit": hits,
                "fail": fails,
                "neutral_draw": neutral,
                "directional_hit_rate": round(hits / n_dir, 4) if n_dir else None,
                "soft_hit_rate": round((hits + 0.5 * neutral) / n, 4) if n else None,
            }
    return out


def _best_horizon_per_lens(matrix: dict[str, dict[str, dict[str, float | int | None]]]) -> dict[str, Any]:
    best: dict[str, Any] = {}
    for lens_id, horizons in matrix.items():
        ranked: list[tuple[str, float]] = []
        for hname, metrics in horizons.items():
            soft = metrics.get("soft_hit_rate")
            if soft is not None:
                ranked.append((hname, float(soft)))
        ranked.sort(key=lambda x: x[1], reverse=True)
        contract = ROLE_MATCHED_HORIZON.get(lens_id)
        contract_soft = None
        if contract and contract in horizons:
            v = horizons[contract].get("soft_hit_rate")
            contract_soft = float(v) if v is not None else None
        best[lens_id] = {
            "best_horizon": ranked[0][0] if ranked else None,
            "best_soft_hit_rate": ranked[0][1] if ranked else None,
            "contract_horizon": contract,
            "contract_soft_hit_rate": contract_soft,
            "ranked_soft": [{"horizon": h, "soft_hit_rate": round(s, 4)} for h, s in ranked[:5]],
        }
    return best


def _combo_ranking(
    matrix: dict[str, dict[str, dict[str, float | int | None]]],
    *,
    horizon: str = "short_1d",
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for lens_id, horizons in matrix.items():
        m = horizons.get(horizon) or {}
        soft = m.get("soft_hit_rate")
        if soft is None:
            continue
        rows.append(
            {
                "lens_id": lens_id,
                "horizon": horizon,
                "soft_hit_rate": soft,
                "directional_hit_rate": m.get("directional_hit_rate"),
                "n_scored": m.get("n_scored"),
            }
        )
    rows.sort(key=lambda r: float(r["soft_hit_rate"]), reverse=True)
    for i, row in enumerate(rows, start=1):
        row["rank"] = i
    return rows


LENS_IDS = (
    "science_core",
    "science_plus_sasang",
    "science_plus_myeongni",
    "science_plus_logos",
    "science_plus_sasang_myeongni",
    "price_only",
    "macro_only",
    "news_only",
)


def _build_labels_and_window(
    csv_path: Path,
    *,
    date_from: str | None,
    date_to: str | None,
    neutral_bps: float,
) -> tuple[list[str], dict[str, dict[str, str]], list[str]]:
    closes = v1._load_closes(csv_path)
    all_trading_days = sorted(closes.keys())
    labels: dict[str, dict[str, str]] = {}
    for i, dk in enumerate(all_trading_days):
        row_labels: dict[str, str] = {}
        for hname, hdays in HORIZONS.items():
            fr = v1._forward_return(closes, all_trading_days, i, hdays)
            if fr is None:
                continue
            row_labels[hname] = v1._direction_from_return(fr, neutral_bps)
        if row_labels:
            labels[dk] = row_labels
    window_days = all_trading_days
    if date_from:
        window_days = [d for d in window_days if d >= date_from]
    if date_to:
        window_days = [d for d in window_days if d <= date_to]
    return all_trading_days, labels, window_days


def _logos_block_for_date(
    eval_date: str,
    *,
    logos_by_day: dict[str, dict[str, Any]] | None,
    logos_lens: Path,
) -> dict[str, Any]:
    if logos_by_day:
        return logos_block_at_date(logos_by_day, eval_date, fallback_global=logos_lens)
    block = logos_global(logos_lens)
    block["input_mode"] = "global_snapshot"
    block["non_gating"] = True
    return block


def build_daily_short_rows(
    *,
    csv_path: Path,
    science_jsonl: Path,
    date_from: str | None,
    date_to: str | None,
    neutral_bps: float,
    myeongni_jsonl: Path,
    sasang_jsonl: Path,
    logos_lens: Path,
    logos_jsonl: Path | None = None,
    myeongni_momentum_window: int,
) -> list[dict[str, Any]]:
    """Per-date short_1d predictions/outcomes for shock/discordant reports."""
    all_trading_days, labels, window_days = _build_labels_and_window(
        csv_path, date_from=date_from, date_to=date_to, neutral_bps=neutral_bps
    )
    closes = v1._load_closes(csv_path)
    science_by = _load_science_by_date(science_jsonl)
    my_by = rows_by_calendar_day(read_jsonl(myeongni_jsonl))
    sa_by = rows_by_calendar_day(read_jsonl(sasang_jsonl))
    logos_by = read_logos_per_date_jsonl(logos_jsonl) if logos_jsonl else None

    rows: list[dict[str, Any]] = []
    for dk in window_days:
        if dk not in labels or "short_1d" not in labels[dk]:
            continue
        idx = all_trading_days.index(dk)
        fr = v1._forward_return(closes, all_trading_days, idx, 1)
        logos_block = _logos_block_for_date(dk, logos_by_day=logos_by, logos_lens=logos_lens)
        preds = _predictions_for_date(
            dk,
            science_row=science_by.get(dk),
            myeongni_by_day=my_by,
            sasang_by_day=sa_by,
            logos_block=logos_block,
            myeongni_momentum_window=myeongni_momentum_window,
        )
        actual = labels[dk]["short_1d"]
        outcomes = {
            lid: v1._outcome(preds.get(lid, "neutral"), actual)
            for lid in LENS_IDS
            if lid in preds
        }
        science_row = science_by.get(dk) or {}
        macro_dir = preds.get("macro_only")
        rows.append(
            {
                "session_date": dk,
                "forward_return_bps": round(float(fr) * 10000.0, 2) if fr is not None else None,
                "actual_short_1d": actual,
                "predictions": preds,
                "outcomes_short_1d": outcomes,
                "science_direction_score": (science_row.get("scores") or {}).get("direction_score"),
                "macro_component_score": (
                    ((science_row.get("components") or {}).get("macro") or {}).get("direction_score")
                ),
                "discordant_science_vs_sasang": preds.get("science_core") != preds.get("sasang")
                and preds.get("science_core") not in (None, "neutral")
                and preds.get("sasang") not in (None, "neutral"),
                "discordant_science_vs_macro_only": preds.get("science_core") != macro_dir
                and preds.get("science_core") not in (None, "neutral")
                and macro_dir not in (None, "neutral"),
            }
        )
    return rows


def run_eval(
    *,
    instrument: str,
    csv_path: Path,
    science_jsonl: Path,
    date_from: str | None,
    date_to: str | None,
    neutral_bps: float,
    myeongni_jsonl: Path,
    sasang_jsonl: Path,
    logos_lens: Path,
    logos_jsonl: Path | None = None,
    myeongni_momentum_window: int,
    required_horizons: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    all_trading_days, labels, window_days = _build_labels_and_window(
        csv_path, date_from=date_from, date_to=date_to, neutral_bps=neutral_bps
    )
    science_by = _load_science_by_date(science_jsonl)
    my_by = rows_by_calendar_day(read_jsonl(myeongni_jsonl))
    sa_by = rows_by_calendar_day(read_jsonl(sasang_jsonl))
    logos_by = read_logos_per_date_jsonl(logos_jsonl) if logos_jsonl else None
    logos_input_mode = "per_date_macro_gate" if logos_by else "global_snapshot"

    req = required_horizons or REQUIRED_HORIZONS
    lens_ids = list(LENS_IDS)

    scored: list[dict[str, Any]] = []
    eval_dates = [d for d in window_days if d in labels and all(h in labels[d] for h in req)]
    for dk in eval_dates:
        logos_block = _logos_block_for_date(dk, logos_by_day=logos_by, logos_lens=logos_lens)
        preds = _predictions_for_date(
            dk,
            science_row=science_by.get(dk),
            myeongni_by_day=my_by,
            sasang_by_day=sa_by,
            logos_block=logos_block,
            myeongni_momentum_window=myeongni_momentum_window,
        )
        for lens_id in lens_ids:
            pred = preds.get(lens_id)
            if pred is None:
                continue
            for hname in HORIZONS:
                if hname not in labels[dk]:
                    continue
                actual = labels[dk][hname]
                scored.append(
                    {
                        "session_date": dk,
                        "lens_id": lens_id,
                        "horizon": hname,
                        "predicted_direction": pred,
                        "actual_direction": actual,
                        "outcome": v1._outcome(pred, actual),
                        "role_matched_horizon": ROLE_MATCHED_HORIZON.get(lens_id),
                        "horizon_is_role_match": ROLE_MATCHED_HORIZON.get(lens_id) == hname,
                    }
                )

    matrix = _rate_matrix(scored, lens_ids)
    best = _best_horizon_per_lens(matrix)
    science_best = best.get("science_core") or {}
    combo_short = _combo_ranking(matrix, horizon="short_1d")
    combo_mid10 = _combo_ranking(matrix, horizon="mid_10d")

    science_alone_short = (matrix.get("science_core") or {}).get("short_1d") or {}
    science_alone_mid5 = (matrix.get("science_core") or {}).get("mid_5d") or {}
    science_alone_macro = (matrix.get("science_core") or {}).get("macro_21d") or {}

    return {
        "schema": "science_core_horizon_empirical_eval_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "boundary_ack": True,
        "instrument": instrument,
        "csv_path": _repo_rel(csv_path),
        "science_jsonl": _repo_rel(science_jsonl),
        "date_from": date_from,
        "date_to": date_to,
        "neutral_bps": neutral_bps,
        "logos_input_mode": logos_input_mode,
        "logos_jsonl": _repo_rel(logos_jsonl),
        "n_eval_dates": len(eval_dates),
        "horizons": HORIZONS,
        "role_matched_horizon": ROLE_MATCHED_HORIZON,
        "required_horizons": list(req),
        "rate_matrix": matrix,
        "best_horizon_by_lens": best,
        "combo_ranking_short_1d": combo_short,
        "combo_ranking_mid_10d": combo_mid10,
        "science_core_summary": {
            "best_horizon": science_best.get("best_horizon"),
            "best_soft_hit_rate": science_best.get("best_soft_hit_rate"),
            "short_1d_soft": science_alone_short.get("soft_hit_rate"),
            "mid_5d_soft": science_alone_mid5.get("soft_hit_rate"),
            "macro_21d_soft": science_alone_macro.get("soft_hit_rate"),
            "always_attach_recommended": False,
            "note": "Set always_attach only after holdout uplift vs science_core alone.",
        },
        "methodology_ko": (
            "Science Core = price+macro+news 정량 레인(사상·명리·성경 제외). "
            "조합은 score 블렌드. Track A·실매매 승격 근거 아님."
        ),
    }


def _science_jsonl_for_instrument(instrument: str, override: Path | None = None) -> Path:
    if override is not None:
        return override
    return DEFAULT_SCIENCE_JSONL_BTC if instrument == "btc" else DEFAULT_SCIENCE_JSONL_KOSPI


def _ensure_science_jsonl(
    *,
    instrument: str,
    csv_path: Path,
    out_path: Path,
    date_from: str | None,
    date_to: str | None,
    apply_overnight: bool,
) -> None:
    from scripts.build_btrack_science_core_per_date_v1 import build_rows, write_jsonl

    rows = build_rows(
        instrument=instrument,
        csv_path=csv_path,
        date_from=date_from,
        date_to=date_to,
        lookback=5,
        apply_overnight=apply_overnight,
        exa_jsonl=ROOT / "reports/exa_macro_news_observation_staging_v1_latest.jsonl",
    )
    write_jsonl(rows, out_path)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--instrument", choices=("kospi", "btc", "both"), default="kospi")
    ap.add_argument("--date-from", type=str, default="2026-01-01")
    ap.add_argument("--date-to", type=str, default="2026-06-08")
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    ap.add_argument("--science-jsonl", type=Path, default=DEFAULT_SCIENCE_JSONL)
    ap.add_argument("--rebuild-science", action="store_true")
    ap.add_argument("--myeongni-jsonl", type=Path, default=DEFAULT_MYEONGNI_JSONL)
    ap.add_argument("--sasang-jsonl", type=Path, default=DEFAULT_SASANG_JSONL)
    ap.add_argument("--logos-lens", type=Path, default=DEFAULT_LOGOS_LENS)
    ap.add_argument("--logos-jsonl", type=Path, default=None, help="Per-date Logos macro gate JSONL (optional).")
    ap.add_argument("--myeongni-momentum-window", type=int, default=5)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact-output", type=Path, default=ART_OUT)
    args = ap.parse_args(argv)

    rebuild = args.rebuild_science
    if args.instrument in ("kospi", "both"):
        kospi_jsonl = _science_jsonl_for_instrument("kospi", args.science_jsonl if args.instrument == "kospi" else None)
        if rebuild or not kospi_jsonl.is_file():
            _ensure_science_jsonl(
                instrument="kospi",
                csv_path=v1.KOSPI_CSV,
                out_path=kospi_jsonl,
                date_from=args.date_from,
                date_to=args.date_to,
                apply_overnight=True,
            )
    if args.instrument in ("btc", "both"):
        btc_jsonl = _science_jsonl_for_instrument("btc")
        if rebuild or not btc_jsonl.is_file():
            _ensure_science_jsonl(
                instrument="btc",
                csv_path=v1.BTC_CSV,
                out_path=btc_jsonl,
                date_from=args.date_from,
                date_to=args.date_to,
                apply_overnight=False,
            )

    legs: dict[str, Any] = {}
    if args.instrument in ("kospi", "both"):
        kospi_jsonl = _science_jsonl_for_instrument("kospi", args.science_jsonl if args.instrument == "kospi" else None)
        legs["kospi"] = run_eval(
            instrument="kospi",
            csv_path=v1.KOSPI_CSV,
            science_jsonl=kospi_jsonl,
            date_from=args.date_from,
            date_to=args.date_to,
            neutral_bps=args.neutral_bps,
            myeongni_jsonl=args.myeongni_jsonl,
            sasang_jsonl=args.sasang_jsonl,
            logos_lens=args.logos_lens,
            logos_jsonl=args.logos_jsonl,
            myeongni_momentum_window=args.myeongni_momentum_window,
        )
    if args.instrument in ("btc", "both"):
        btc_jsonl = _science_jsonl_for_instrument("btc")
        legs["btc"] = run_eval(
            instrument="btc",
            csv_path=v1.BTC_CSV,
            science_jsonl=btc_jsonl,
            date_from=args.date_from,
            date_to=args.date_to,
            neutral_bps=args.neutral_bps,
            myeongni_jsonl=args.myeongni_jsonl,
            sasang_jsonl=args.sasang_jsonl,
            logos_lens=args.logos_lens,
            logos_jsonl=args.logos_jsonl,
            myeongni_momentum_window=args.myeongni_momentum_window,
        )

    doc = {
        "schema": "science_core_horizon_empirical_eval_bundle_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "date_from": args.date_from,
        "date_to": args.date_to,
        "legs": legs,
        "summary": {
            leg: {
                "science_best_horizon": legs[leg]["science_core_summary"].get("best_horizon"),
                "science_best_soft": legs[leg]["science_core_summary"].get("best_soft_hit_rate"),
                "top_combo_short_1d": (legs[leg].get("combo_ranking_short_1d") or [{}])[0].get("lens_id"),
                "n_eval_dates": legs[leg]["n_eval_dates"],
            }
            for leg in legs
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.artifact_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    art = legs.get("kospi") or next(iter(legs.values()), doc)
    args.artifact_output.write_text(json.dumps(art, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    k = legs.get("kospi", {}).get("science_core_summary", {})
    print(
        f"WROTE: {args.output.resolve()} science_best={k.get('best_horizon')} "
        f"soft={k.get('best_soft_hit_rate')} n={legs.get('kospi', {}).get('n_eval_dates')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
