#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Three-lens horizon alignment empirical eval [HYPO][research_only].

Tests the role contract:
  logos      -> macro horizon (21 trading days forward)
  myeongni   -> mid horizon (10 trading days forward)
  sasang     -> short horizon (1 trading day forward)

Per-date causal lens signals from calendar JSONL; realized labels from OHLCV.
Compares matched vs mismatched horizons per lens (not Track A promotion).
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
    logos_global,
    read_jsonl,
    row_asof,
    rows_by_calendar_day,
    score_myeongni_at_date,
    causal_rows_through,
    score_sasang_at_date,
    sign_to_dir,
)
from scripts.build_kospi_june2026_daily_prophecy_calendar_v1 import (  # noqa: E402
    _score_from_session_pillars,
)
from scripts.build_myeongni_jsonl_from_manseryeok_session_v1 import (  # noqa: E402
    _mapping_from_score,
)
from scripts.kospi_june2026_multilens_blend_v1 import (  # noqa: E402
    _dir_from_score,
    _lens_direction_from_artifact,
)
from scripts.logos_shadow_eval_lib import load_kospi_yf_rows  # noqa: E402

KOSPI_CSV = ROOT / "research/market_data/kospi_daily_external_yf.csv"
BTC_CSV = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_PANEL = ROOT / "reports/btrack_session_myeongni_panel_252d_v1.csv"
MACRO_LENS = ROOT / "docs/final/artifacts/macro_independent_lens_latest.json"
DEFAULT_OUT = ROOT / "reports/three_lens_horizon_empirical_eval_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/three_lens_horizon_empirical_eval_latest.json"

HORIZONS: dict[str, int] = {
    "short_1d": 1,
    "mid_10d": 10,
    "macro_21d": 21,
}

ROLE_MATCHED_HORIZON: dict[str, str] = {
    "logos": "macro_21d",
    "myeongni": "mid_10d",
    "sasang": "short_1d",
    "macro_independent": "macro_21d",
    "session_myeongni": "short_1d",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_closes(csv_path: Path) -> dict[str, float]:
    rows = load_kospi_yf_rows(csv_path)
    return {str(r["date"])[:10]: float(r["close"]) for r in rows if r.get("date")}


def _load_panel(panel_csv: Path) -> dict[str, dict[str, str]]:
    import csv

    out: dict[str, dict[str, str]] = {}
    if not panel_csv.is_file():
        return out
    with panel_csv.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            dk = str(row.get("session_local_date", ""))[:10]
            if dk:
                out[dk] = row
    return out


def _direction_from_return(ret: float, neutral_bps: float) -> str:
    thr = neutral_bps / 10000.0
    if ret > thr:
        return "bull"
    if ret < -thr:
        return "bear"
    return "neutral"


def _score_to_direction(score: float, *, threshold: float = 0.08) -> str:
    if score > threshold:
        return "bull"
    if score < -threshold:
        return "bear"
    return "neutral"


def _outcome(pred: str, actual: str) -> str:
    if actual == "neutral" or pred == "neutral":
        return "NEUTRAL_DRAW"
    if pred == actual:
        return "HIT"
    return "FAIL"


def _forward_return(closes: dict[str, float], trading_days: list[str], idx: int, horizon: int) -> float | None:
    if idx + horizon >= len(trading_days):
        return None
    d0 = trading_days[idx]
    d1 = trading_days[idx + horizon]
    c0 = closes.get(d0)
    c1 = closes.get(d1)
    if c0 is None or c1 is None or c0 == 0:
        return None
    return (c1 - c0) / c0


def _build_forward_labels(
    trading_days: list[str],
    closes: dict[str, float],
    *,
    neutral_bps: float,
) -> dict[str, dict[str, str]]:
    labels: dict[str, dict[str, str]] = {}
    for i, dk in enumerate(trading_days):
        row_labels: dict[str, str] = {}
        for hname, hdays in HORIZONS.items():
            fr = _forward_return(closes, trading_days, i, hdays)
            if fr is None:
                continue
            row_labels[hname] = _direction_from_return(fr, neutral_bps)
        if row_labels:
            labels[dk] = row_labels
    return labels


def _lens_predictions_for_date(
    dk: str,
    *,
    myeongni_by_day: dict[str, dict[str, Any]],
    sasang_by_day: dict[str, dict[str, Any]],
    logos_block: dict[str, Any],
    macro_dir: str,
    panel_row: dict[str, str] | None,
    neutral_band: float,
    myeongni_momentum_window: int,
) -> dict[str, str]:
    my_day, _ = row_asof(myeongni_by_day, dk)
    sa_day, sa_asof = row_asof(sasang_by_day, dk)
    my_hist = causal_rows_through(myeongni_by_day, dk)
    my = score_myeongni_at_date(
        my_hist,
        eval_date=dk,
        matched_day=my_day,
        momentum_window=myeongni_momentum_window,
    )
    sa = score_sasang_at_date(sa_asof, matched_day=sa_day, eval_date=dk)

    logos_sign = int(logos_block.get("sign") or 0)
    preds: dict[str, str] = {
        "myeongni": _score_to_direction(float(my.get("direction_score") or 0.0)),
        "sasang": _score_to_direction(float(sa.get("direction_score") or 0.0)),
        "logos": sign_to_dir(logos_sign),
        "macro_independent": macro_dir,
    }

    if panel_row:
        pillars = {
            "year": str(panel_row.get("year_pillar") or ""),
            "month": str(panel_row.get("month_pillar") or ""),
            "day": str(panel_row.get("day_pillar") or ""),
            "hour": str(panel_row.get("hour_pillar") or ""),
        }
        session_score = _score_from_session_pillars(pillars)
        session_map = _mapping_from_score(session_score, neutral_band)
        if session_map == "sideways":
            preds["session_myeongni"] = "neutral"
        else:
            preds["session_myeongni"] = session_map
    else:
        preds["session_myeongni"] = "neutral"

    return preds


def _rate_matrix(
    scored: list[dict[str, Any]],
) -> dict[str, dict[str, dict[str, float | int | None]]]:
    """lens -> horizon -> metrics."""
    out: dict[str, dict[str, dict[str, float | int | None]]] = {}
    for lens_id in ROLE_MATCHED_HORIZON:
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


def _alignment_verdict(
    matrix: dict[str, dict[str, dict[str, float | int | None]]],
    *,
    min_n: int,
    min_soft_delta: float,
) -> dict[str, Any]:
    per_lens: dict[str, Any] = {}
    supported = 0
    tested = 0
    for lens_id, matched_h in ROLE_MATCHED_HORIZON.items():
        lens_rows = matrix.get(lens_id) or {}
        matched = lens_rows.get(matched_h) or {}
        matched_soft = matched.get("soft_hit_rate")
        matched_n = int(matched.get("n_scored") or 0)
        mismatches: dict[str, float | None] = {}
        for hname in HORIZONS:
            if hname == matched_h:
                continue
            mismatches[hname] = (lens_rows.get(hname) or {}).get("soft_hit_rate")

        best_mismatch_name = None
        best_mismatch_soft = None
        for hname, val in mismatches.items():
            if val is None:
                continue
            if best_mismatch_soft is None or float(val) > float(best_mismatch_soft):
                best_mismatch_soft = float(val)
                best_mismatch_name = hname

        delta = None
        passes = False
        if matched_soft is not None and best_mismatch_soft is not None and matched_n >= min_n:
            tested += 1
            delta = round(float(matched_soft) - float(best_mismatch_soft), 4)
            passes = delta >= min_soft_delta
            if passes:
                supported += 1

        per_lens[lens_id] = {
            "contract_role": matched_h,
            "matched_horizon": matched_h,
            "matched_soft_hit_rate": matched_soft,
            "matched_n_scored": matched_n,
            "best_mismatch_horizon": best_mismatch_name,
            "best_mismatch_soft_hit_rate": best_mismatch_soft,
            "soft_delta_matched_minus_best_mismatch": delta,
            "alignment_pass": passes,
        }

    overall = False
    if tested >= 3:
        overall = supported >= 2 and supported / tested >= 0.67

    return {
        "min_n_scored": min_n,
        "min_soft_delta": min_soft_delta,
        "lenses_tested": tested,
        "lenses_alignment_pass": supported,
        "per_lens": per_lens,
        "hypothesis_supported": overall,
        "verdict_ko": (
            "역할-호라이즌 정렬 일부 지지"
            if overall
            else "역할-호라이즌 정렬 실증 미달(계약 유지·연구 계속)"
        ),
        "note": "Not Track A proof. Logos may use global snapshot; per-date macro path still limited.",
    }


def run_eval(
    *,
    instrument: str,
    csv_path: Path,
    date_from: str | None,
    date_to: str | None,
    neutral_bps: float,
    neutral_band: float,
    myeongni_jsonl: Path,
    sasang_jsonl: Path,
    logos_lens: Path,
    panel_csv: Path,
    myeongni_momentum_window: int,
    min_n: int,
    min_soft_delta: float,
) -> dict[str, Any]:
    closes = _load_closes(csv_path)
    trading_days = sorted(closes.keys())
    if date_from:
        trading_days = [d for d in trading_days if d >= date_from]
    if date_to:
        trading_days = [d for d in trading_days if d <= date_to]

    labels = _build_forward_labels(trading_days, closes, neutral_bps=neutral_bps)
    my_by = rows_by_calendar_day(read_jsonl(myeongni_jsonl))
    sa_by = rows_by_calendar_day(read_jsonl(sasang_jsonl))
    logos_block = logos_global(logos_lens)
    macro_dir, _, macro_ok = _lens_direction_from_artifact(MACRO_LENS)
    if not macro_ok:
        macro_dir = "neutral"
    panel = _load_panel(panel_csv)

    scored: list[dict[str, Any]] = []
    eval_dates = [d for d in trading_days if d in labels and all(h in labels[d] for h in HORIZONS)]
    for dk in eval_dates:
        preds = _lens_predictions_for_date(
            dk,
            myeongni_by_day=my_by,
            sasang_by_day=sa_by,
            logos_block=logos_block,
            macro_dir=macro_dir,
            panel_row=panel.get(dk),
            neutral_band=neutral_band,
            myeongni_momentum_window=myeongni_momentum_window,
        )
        for lens_id, pred in preds.items():
            for hname in HORIZONS:
                actual = labels[dk][hname]
                scored.append(
                    {
                        "session_date": dk,
                        "lens_id": lens_id,
                        "horizon": hname,
                        "predicted_direction": pred,
                        "actual_direction": actual,
                        "outcome": _outcome(pred, actual),
                        "role_matched_horizon": ROLE_MATCHED_HORIZON.get(lens_id),
                        "horizon_is_role_match": ROLE_MATCHED_HORIZON.get(lens_id) == hname,
                    }
                )

    matrix = _rate_matrix(scored)
    alignment = _alignment_verdict(matrix, min_n=min_n, min_soft_delta=min_soft_delta)

    return {
        "schema": "three_lens_horizon_empirical_eval_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "instrument": instrument,
        "csv_path": str(csv_path.relative_to(ROOT)).replace("\\", "/"),
        "date_from": date_from,
        "date_to": date_to,
        "neutral_bps": neutral_bps,
        "neutral_band": neutral_band,
        "n_eval_dates": len(eval_dates),
        "horizons": HORIZONS,
        "role_matched_horizon": ROLE_MATCHED_HORIZON,
        "inputs": {
            "myeongni_jsonl": str(myeongni_jsonl.relative_to(ROOT)).replace("\\", "/"),
            "sasang_jsonl": str(sasang_jsonl.relative_to(ROOT)).replace("\\", "/"),
            "logos_lens_json": str(logos_lens.relative_to(ROOT)).replace("\\", "/"),
            "macro_lens_json": str(MACRO_LENS.relative_to(ROOT)).replace("\\", "/"),
            "panel_csv": str(panel_csv.relative_to(ROOT)).replace("\\", "/"),
            "myeongni_momentum_window": myeongni_momentum_window,
            "logos_signal_mode": "global_snapshot_non_gating",
            "macro_independent_signal_mode": "global_snapshot",
        },
        "rate_matrix": matrix,
        "alignment_verdict": alignment,
        "methodology_ko": (
            "일자별 인과 JSONL 렌즈 신호 vs OHLCV 선행 수익률 방향 라벨. "
            "성경(Logos)은 글로벌 스냅샷 한계를 명시. Track A·실매매 승격 근거 아님."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--instrument", choices=("kospi", "btc", "both"), default="both")
    ap.add_argument("--date-from", type=str, default="2026-01-01")
    ap.add_argument("--date-to", type=str, default="2026-04-30")
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    ap.add_argument("--neutral-band", type=float, default=0.06)
    ap.add_argument("--myeongni-jsonl", type=Path, default=DEFAULT_MYEONGNI_JSONL)
    ap.add_argument("--sasang-jsonl", type=Path, default=DEFAULT_SASANG_JSONL)
    ap.add_argument("--logos-lens", type=Path, default=DEFAULT_LOGOS_LENS)
    ap.add_argument("--panel-csv", type=Path, default=DEFAULT_PANEL)
    ap.add_argument("--myeongni-momentum-window", type=int, default=5)
    ap.add_argument("--min-n", type=int, default=20)
    ap.add_argument("--min-soft-delta", type=float, default=0.03)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact-output", type=Path, default=ART_OUT)
    args = ap.parse_args(argv)

    legs: dict[str, Any] = {}
    if args.instrument in ("kospi", "both"):
        legs["kospi"] = run_eval(
            instrument="kospi",
            csv_path=KOSPI_CSV,
            date_from=args.date_from,
            date_to=args.date_to,
            neutral_bps=args.neutral_bps,
            neutral_band=args.neutral_band,
            myeongni_jsonl=args.myeongni_jsonl,
            sasang_jsonl=args.sasang_jsonl,
            logos_lens=args.logos_lens,
            panel_csv=args.panel_csv,
            myeongni_momentum_window=args.myeongni_momentum_window,
            min_n=args.min_n,
            min_soft_delta=args.min_soft_delta,
        )
    if args.instrument in ("btc", "both"):
        legs["btc"] = run_eval(
            instrument="btc",
            csv_path=BTC_CSV,
            date_from=args.date_from,
            date_to=args.date_to,
            neutral_bps=args.neutral_bps,
            neutral_band=args.neutral_band,
            myeongni_jsonl=args.myeongni_jsonl,
            sasang_jsonl=args.sasang_jsonl,
            logos_lens=args.logos_lens,
            panel_csv=args.panel_csv,
            myeongni_momentum_window=args.myeongni_momentum_window,
            min_n=args.min_n,
            min_soft_delta=args.min_soft_delta,
        )

    doc = {
        "schema": "three_lens_horizon_empirical_eval_bundle_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "date_from": args.date_from,
        "date_to": args.date_to,
        "legs": legs,
        "summary": {
            leg: {
                "hypothesis_supported": legs[leg]["alignment_verdict"]["hypothesis_supported"],
                "verdict_ko": legs[leg]["alignment_verdict"]["verdict_ko"],
                "n_eval_dates": legs[leg]["n_eval_dates"],
            }
            for leg in legs
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.artifact_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    art_payload = legs.get("kospi") or doc
    args.artifact_output.write_text(json.dumps(art_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    kospi_v = legs.get("kospi", {}).get("alignment_verdict", {})
    print(
        f"WROTE: {args.output.resolve()} kospi_supported={kospi_v.get('hypothesis_supported')} "
        f"n_dates={legs.get('kospi', {}).get('n_eval_dates')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
