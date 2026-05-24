#!/usr/bin/env python3
"""Shared holdout feature dump + metrics for wrong_dir auxiliary layer."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

HOLDOUT_7_DEFAULT = [
    "2026-04-02",
    "2026-04-08",
    "2026-04-14",
    "2026-04-24",
    "2026-04-27",
    "2026-05-07",
    "2026-05-11",
]
BTC_CSV = ROOT / "research/market_data/btc_daily_external_yf.csv"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def holdout_dates_from_cf(cf_path: Path) -> list[str]:
    if cf_path.is_file():
        doc = _load(cf_path)
        dates = doc.get("wrong_direction_dates")
        if isinstance(dates, list) and dates:
            return [str(d)[:10] for d in dates]
    return list(HOLDOUT_7_DEFAULT)


def enrich_btc_row(
    row: dict[str, Any],
    *,
    actual_by_date: dict[str, str],
    holdout_set: set[str],
    ohlc: dict[str, dict[str, float]],
    closes: dict[str, float],
) -> dict[str, Any]:
    from scripts.btrack_causal_ohlc_features_v1 import (
        last_daily_return_at_eval,
        overnight_return_at_eval,
        prior_range_position_at_eval,
        realized_vol_5d_at_eval,
        vol_regime_high,
    )

    ed = str(row.get("eval_date") or "")[:10]
    ovn = overnight_return_at_eval(ohlc, ed)
    prp = prior_range_position_at_eval(ohlc, ed)
    rv = realized_vol_5d_at_eval(closes, ed)
    last_ret = last_daily_return_at_eval(closes, ed)
    pred = str(row.get("predicted_direction") or "").lower()
    act = str(actual_by_date.get(ed) or "").lower()
    prelim = str(row.get("preliminary_direction") or pred).lower()

    is_holdout = ed in holdout_set
    wrong_dir = pred in ("bull", "bear") and act in ("bull", "bear") and pred != act
    hit = pred == act and pred in ("bull", "bear", "neutral")

    out = dict(row)
    out.update(
        {
            "eval_date": ed,
            "actual_direction": act or None,
            "overnight_return": ovn,
            "prior_range_position": prp,
            "realized_vol_5d": rv,
            "last_daily_return": last_ret,
            "vol_regime_high": vol_regime_high(rv, threshold=0.03) if rv is not None else False,
            "is_holdout_7": is_holdout,
            "is_wrong_direction": wrong_dir,
            "is_hit_all_rows": hit,
            "preliminary_bull": prelim == "bull",
            "predicted_bull": pred == "bull",
        }
    )
    price_lv = row.get("lens_values") if isinstance(row.get("lens_values"), dict) else {}
    price_blob = price_lv.get("price") if isinstance(price_lv.get("price"), dict) else {}
    if price_blob.get("score") is not None:
        out["price_lens_score"] = price_blob.get("score")
    return out


def enrich_per_date_doc_btc(
    per_date_doc: dict[str, Any],
    holdout_dates: list[str],
    *,
    instrument: str = "btc",
) -> dict[str, Any]:
    """Attach OHLC causal features to BTC per-date rows (for advisory/auxiliary)."""
    from scripts.btrack_causal_ohlc_features_v1 import load_btc_ohlc_by_date

    inst = instrument.strip().lower()
    holdout_set = set(holdout_dates)
    ohlc = load_btc_ohlc_by_date(BTC_CSV)
    closes = {d: v["close"] for d, v in ohlc.items()}
    new_rows: list[dict[str, Any]] = []
    for r in per_date_doc.get("rows") or []:
        if not isinstance(r, dict) or str(r.get("instrument") or "").lower() != inst:
            new_rows.append(r)
            continue
        new_rows.append(
            enrich_btc_row(
                r,
                actual_by_date={},
                holdout_set=holdout_set,
                ohlc=ohlc,
                closes=closes,
            )
        )
    out = dict(per_date_doc)
    out["rows"] = new_rows
    return out


def build_feature_dump(
    *,
    per_date_doc: dict[str, Any],
    score_doc: dict[str, Any],
    holdout_dates: list[str],
    neutral_bps: float = 5.0,
) -> dict[str, Any]:
    from scripts.btrack_causal_ohlc_features_v1 import actual_direction_at_eval, load_btc_ohlc_by_date

    ohlc = load_btc_ohlc_by_date(BTC_CSV)
    closes = {d: v["close"] for d, v in ohlc.items()}
    actual_by_date: dict[str, str] = {}
    for r in score_doc.get("rows") or []:
        if not isinstance(r, dict) or str(r.get("instrument") or "").lower() != "btc":
            continue
        ed = str(r.get("eval_date") or "")[:10]
        act = r.get("actual_direction")
        if act:
            actual_by_date[ed] = str(act).lower()
    for r in per_date_doc.get("rows") or []:
        if not isinstance(r, dict) or str(r.get("instrument") or "").lower() != "btc":
            continue
        ed = str(r.get("eval_date") or "")[:10]
        if ed not in actual_by_date or not actual_by_date[ed]:
            fallback = actual_direction_at_eval(closes, ed, neutral_bps=neutral_bps)
            if fallback:
                actual_by_date[ed] = fallback
    holdout_set = set(holdout_dates)
    ohlc = load_btc_ohlc_by_date(BTC_CSV)
    closes = {d: v["close"] for d, v in ohlc.items()}
    rows: list[dict[str, Any]] = []
    for r in per_date_doc.get("rows") or []:
        if not isinstance(r, dict) or str(r.get("instrument") or "").lower() != "btc":
            continue
        rows.append(
            enrich_btc_row(
                r,
                actual_by_date=actual_by_date,
                holdout_set=holdout_set,
                ohlc=ohlc,
                closes=closes,
            )
        )

    holdout_rows = [r for r in rows if r.get("is_holdout_7")]
    train_wrong = [r["eval_date"] for r in rows if r.get("is_wrong_direction") and not r.get("is_holdout_7")]

    return {
        "schema": "btrack_wrong_dir_holdout_features_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "holdout_7_dates": holdout_dates,
        "train_wrong_direction_dates": sorted(train_wrong),
        "n_rows": len(rows),
        "n_holdout_7": len(holdout_rows),
        "n_wrong_direction_total": sum(1 for r in rows if r.get("is_wrong_direction")),
        "n_wrong_direction_holdout": sum(1 for r in holdout_rows if r.get("is_wrong_direction")),
        "rows": rows,
        "operator_line": (
            f"- [MKM-HOLDOUT-DUMP] n={len(rows)} holdout7={len(holdout_rows)} "
            f"wrong_dir={sum(1 for r in rows if r.get('is_wrong_direction'))} "
            f"train_wrong={len(train_wrong)}"
        ),
    }


def cohort_metrics_wrong_dir(
    rows: list[dict[str, Any]],
    *,
    dates_filter: set[str] | None = None,
    holdout_only: bool | None = None,
    use_adjusted: bool = False,
) -> dict[str, Any]:
    """Metrics on wrong-direction days only (bear_fix / neutralized)."""
    subset = [r for r in rows if r.get("is_wrong_direction")]
    if holdout_only is True:
        subset = [r for r in subset if r.get("is_holdout_7")]
    elif holdout_only is False:
        subset = [r for r in subset if not r.get("is_holdout_7")]
    if dates_filter is not None:
        subset = [r for r in subset if str(r.get("eval_date"))[:10] in dates_filter]
    n = len(subset)
    bear_fix = neutralized = 0
    for r in subset:
        pred = str(
            r.get("adjusted_direction") if use_adjusted else r.get("predicted_direction") or ""
        ).lower()
        act = str(r.get("actual_direction") or "").lower()
        if act == "bear" and pred == "bear":
            bear_fix += 1
        if pred == "neutral":
            neutralized += 1
    return {
        "n_wrong_dir_days": n,
        "bear_fix": bear_fix,
        "neutralized": neutralized,
        "bear_fix_rate": round(bear_fix / n, 6) if n else None,
    }


def wrong_dir_cohort_with_auxiliary(
    per_doc: dict[str, Any],
    dump: dict[str, Any],
    holdout_dates: list[str],
    layer: dict[str, Any],
    *,
    holdout_only: bool | None,
) -> dict[str, Any]:
    """Wrong-dir bear_fix/neutralized using enriched per-date rows + apply_auxiliary_to_row."""
    from scripts.btrack_wrong_dir_auxiliary_layer_v1 import apply_auxiliary_to_row

    holdout_set = set(holdout_dates)
    enriched = enrich_per_date_doc_btc(per_doc, holdout_dates)
    dump_by = {
        str(r.get("eval_date"))[:10]: r for r in dump.get("rows") or [] if isinstance(r, dict)
    }
    bear_fix = neutralized = n = 0
    for r in enriched.get("rows") or []:
        if not isinstance(r, dict) or str(r.get("instrument") or "").lower() != "btc":
            continue
        ed = str(r.get("eval_date") or "")[:10]
        base = dump_by.get(ed) or {}
        act = str(base.get("actual_direction") or r.get("actual_direction") or "").lower()
        pred = str(r.get("predicted_direction") or "").lower()
        is_h7 = ed in holdout_set
        if holdout_only is True and not is_h7:
            continue
        if holdout_only is False and is_h7:
            continue
        if not (pred in ("bull", "bear") and act in ("bull", "bear") and pred != act):
            continue
        n += 1
        row = dict(r)
        row["is_holdout_7"] = is_h7
        row["actual_direction"] = act
        adj = apply_auxiliary_to_row(row, layer)
        apred = str(adj.get("adjusted_direction") or pred).lower()
        if act == "bear" and apred == "bear":
            bear_fix += 1
        if apred == "neutral":
            neutralized += 1
    return {
        "n_wrong_dir_days": n,
        "bear_fix": bear_fix,
        "neutralized": neutralized,
        "bear_fix_rate": round(bear_fix / n, 6) if n else None,
    }


def cohort_metrics(
    rows: list[dict[str, Any]],
    *,
    dates_filter: set[str] | None = None,
    use_adjusted: bool = False,
) -> dict[str, Any]:
    subset = rows
    if dates_filter is not None:
        subset = [r for r in rows if str(r.get("eval_date"))[:10] in dates_filter]
    n = len(subset)
    hits = 0
    bear_fix = 0
    neutralized = 0
    for r in subset:
        pred = str(
            r.get("adjusted_direction") if use_adjusted else r.get("predicted_direction") or ""
        ).lower()
        act = str(r.get("actual_direction") or "").lower()
        if pred == act:
            hits += 1
        if r.get("is_wrong_direction") and act == "bear" and pred == "bear":
            bear_fix += 1
        if r.get("is_wrong_direction") and pred == "neutral":
            neutralized += 1
    return {
        "n_evaluated": n,
        "price_hits": hits,
        "price_directional_hit_rate": round(hits / n, 6) if n else None,
        "holdout_wrong_dir_bear_fix": bear_fix,
        "holdout_wrong_dir_neutralized": neutralized,
    }
