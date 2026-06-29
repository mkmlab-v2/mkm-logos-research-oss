#!/usr/bin/env python3
"""Per-date regime_map Field gated causal blocked WF (B-track, reports lane).

Uses ``field_regime_per_date_attachment_hypo_v1`` quad_doy primary per eval_date.
Stress regimes -> baseline; else -> fixed causal prior-return (0.01/0.02).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
DEFAULT_ATTACHMENT = ROOT / "reports/field_regime_per_date_attachment_hypo_v1_latest.json"
DEFAULT_KOSPI_CSV = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_BTC_CSV = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports/prophecy_causal_regime_map_perdate_gated_walkforward_hypo_v1_latest.json"
SCHEMA = "prophecy_causal_regime_map_perdate_gated_walkforward_hypo_v1"
VALID = {"bull", "bear", "neutral"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _prior_map(csv_path: Path) -> dict[str, float]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.logos_shadow_eval_lib import load_kospi_yf_rows

    rows = load_kospi_yf_rows(csv_path)
    out: dict[str, float] = {}
    for i in range(2, len(rows)):
        ed = str(rows[i]["date"])[:10]
        try:
            c1 = float(rows[i - 1]["close"])
            c2 = float(rows[i - 2]["close"])
        except (TypeError, ValueError):
            continue
        if c2 == 0.0:
            continue
        out[ed] = (c1 - c2) / c2
    return out


def _pred_causal(pr: float | None, *, low: float, high: float, fallback: str) -> str:
    if pr is None:
        return fallback if fallback in VALID else "neutral"
    if pr <= low:
        return "bear"
    if pr >= high:
        return "bull"
    return "neutral"


def _metrics(rows: list[dict[str, Any]], preds: list[str]) -> dict[str, Any]:
    n = h = 0
    for r, p in zip(rows, preds):
        a = str(r.get("actual_direction") or "").strip().lower()
        if p not in VALID or a not in VALID:
            continue
        n += 1
        if p == a:
            h += 1
    return {
        "price_directional_hit_rate": round(h / n, 6) if n else None,
        "n_evaluated": n,
        "price_hits": h,
    }


def _blocked_folds(dates_sorted: list[str], n_folds: int) -> list[tuple[list[str], list[str]]]:
    n = len(dates_sorted)
    base = n // n_folds
    rem = n % n_folds
    blocks: list[list[str]] = []
    idx = 0
    for b in range(n_folds):
        sz = base + (1 if b < rem else 0)
        blocks.append(dates_sorted[idx : idx + sz])
        idx += sz
    folds: list[tuple[list[str], list[str]]] = []
    for f in range(1, n_folds):
        train: list[str] = []
        for b in range(f):
            train.extend(blocks[b])
        test = blocks[f]
        if train and test:
            folds.append((train, test))
    return folds


def _date_regime_map(attachment: dict[str, Any], *, method: str) -> dict[str, str | None]:
    key = "quad_doy_attachment" if method == "quad_doy" else "ohlcv_state_attachment"
    out: dict[str, str | None] = {}
    for row in attachment.get("rows") or []:
        if not isinstance(row, dict):
            continue
        ed = str(row.get("eval_date") or "")[:10]
        attach = row.get(key) or {}
        out[ed] = attach.get("primary_regime_id") if isinstance(attach, dict) else None
    return out


def _preds_gated(
    rows: list[dict[str, Any]],
    *,
    km: dict[str, float],
    bm: dict[str, float],
    date_regime: dict[str, str | None],
    stress_ids: frozenset[str],
    low: float,
    high: float,
) -> tuple[list[str], dict[str, int]]:
    preds: list[str] = []
    counts = {"stress_baseline": 0, "calm_causal": 0, "missing_regime_baseline": 0}
    for r in rows:
        inst = str(r.get("instrument") or "").strip().lower()
        ed = str(r.get("eval_date") or "").strip()[:10]
        old = str(r.get("predicted_direction") or "").strip().lower()
        fallback = old if old in VALID else "neutral"
        rid = date_regime.get(ed)
        if not rid:
            preds.append(fallback)
            counts["missing_regime_baseline"] += 1
            continue
        if rid in stress_ids:
            preds.append(fallback)
            counts["stress_baseline"] += 1
        else:
            mp = km if inst == "kospi" else bm
            preds.append(_pred_causal(mp.get(ed), low=low, high=high, fallback=fallback))
            counts["calm_causal"] += 1
    return preds, counts


def main() -> int:
    ap = argparse.ArgumentParser(description="Per-date regime_map gated causal blocked WF.")
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--attachment-json", type=Path, default=DEFAULT_ATTACHMENT)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI_CSV)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC_CSV)
    ap.add_argument("--attachment-method", choices=("quad_doy", "ohlcv_state"), default="quad_doy")
    ap.add_argument("--low-thr", type=float, default=0.01)
    ap.add_argument("--high-thr", type=float, default=0.02)
    ap.add_argument("--stress-regime-ids", type=str, default="imf,lehman,covid")
    ap.add_argument("--n-folds", type=int, default=5)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    stress_ids = frozenset(x.strip() for x in args.stress_regime_ids.split(",") if x.strip())
    doc = _load_json(args.score_json)
    attachment = _load_json(args.attachment_json)
    rows = [r for r in doc.get("rows", []) if isinstance(r, dict)]
    if not rows:
        raise SystemExit("score rows[] empty")

    date_regime = _date_regime_map(attachment, method=args.attachment_method)
    km = _prior_map(args.kospi_csv)
    bm = _prior_map(args.btc_csv)

    dates = sorted({str(r.get("eval_date") or "")[:10] for r in rows if str(r.get("eval_date") or "").strip()})
    n_folds = max(2, min(int(args.n_folds), len(dates)))
    fold_specs = _blocked_folds(dates, n_folds)

    base_preds = [str(r.get("predicted_direction") or "").strip().lower() for r in rows]
    gated_preds, gate_counts = _preds_gated(
        rows,
        km=km,
        bm=bm,
        date_regime=date_regime,
        stress_ids=stress_ids,
        low=args.low_thr,
        high=args.high_thr,
    )

    in_base = _metrics(rows, base_preds)
    in_gated = _metrics(rows, gated_preds)

    gated_test_accs: list[float] = []
    fixed_test_accs: list[float] = []
    base_test_accs: list[float] = []
    fold_out: list[dict[str, Any]] = []

    for fi, (_train_dates, test_dates) in enumerate(fold_specs):
        test_set = set(test_dates)
        test = [r for r in rows if str(r.get("eval_date") or "")[:10] in test_set]
        base_p = [str(r.get("predicted_direction") or "").strip().lower() for r in test]
        gated_p, fold_gate = _preds_gated(
            test,
            km=km,
            bm=bm,
            date_regime=date_regime,
            stress_ids=stress_ids,
            low=args.low_thr,
            high=args.high_thr,
        )
        fixed_p = []
        for r in test:
            inst = str(r.get("instrument") or "").strip().lower()
            ed = str(r.get("eval_date") or "").strip()[:10]
            old = str(r.get("predicted_direction") or "").strip().lower()
            mp = km if inst == "kospi" else bm
            fixed_p.append(_pred_causal(mp.get(ed), low=args.low_thr, high=args.high_thr, fallback=old))

        m_base = _metrics(test, base_p)
        m_gated = _metrics(test, gated_p)
        m_fixed = _metrics(test, fixed_p)
        b_acc = float(m_base["price_directional_hit_rate"] or 0.0)
        g_acc = float(m_gated["price_directional_hit_rate"] or 0.0)
        f_acc = float(m_fixed["price_directional_hit_rate"] or 0.0)
        base_test_accs.append(b_acc)
        gated_test_accs.append(g_acc)
        fixed_test_accs.append(f_acc)
        fold_out.append(
            {
                "fold_index": fi,
                "test_dates": test_dates,
                "n_test_rows": len(test),
                "gate_counts_test": fold_gate,
                "baseline_test": m_base,
                "perdate_regime_gated_test": {**m_gated, "delta_vs_baseline": round(g_acc - b_acc, 6)},
                "fixed_causal_test": {**m_fixed, "delta_vs_baseline": round(f_acc - b_acc, 6)},
            }
        )

    def _agg(accs: list[float]) -> dict[str, Any]:
        if not accs:
            return {"mean_test_accuracy": None}
        mean = sum(accs) / len(accs)
        var = sum((x - mean) ** 2 for x in accs) / len(accs)
        return {
            "mean_test_accuracy": round(mean, 6),
            "stdev_test_accuracy": round(math.sqrt(var), 6),
            "min_test_accuracy": round(min(accs), 6),
            "max_test_accuracy": round(max(accs), 6),
        }

    out = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "production_score_unmodified": True,
        "field_layer": {
            "attachment_json": str(args.attachment_json),
            "attachment_method": args.attachment_method,
            "stress_regime_ids": sorted(stress_ids),
        },
        "inputs": {
            "score_json": str(args.score_json),
            "fixed_low_thr": args.low_thr,
            "fixed_high_thr": args.high_thr,
            "n_folds": n_folds,
            "n_distinct_eval_dates": len(dates),
        },
        "in_sample_full_panel": {
            "baseline": in_base,
            "perdate_regime_gated": in_gated,
            "delta_gated_minus_baseline": round(
                float(in_gated["price_directional_hit_rate"] or 0.0)
                - float(in_base["price_directional_hit_rate"] or 0.0),
                6,
            ),
            "gate_counts_full_panel": gate_counts,
        },
        "blocked_walkforward_test_only": {
            "perdate_regime_gated": _agg(gated_test_accs),
            "fixed_causal_always": _agg(fixed_test_accs),
            "baseline_panel": _agg(base_test_accs),
            "delta_gated_minus_fixed_mean_test": round(
                (sum(gated_test_accs) / len(gated_test_accs) if gated_test_accs else 0.0)
                - (sum(fixed_test_accs) / len(fixed_test_accs) if fixed_test_accs else 0.0),
                6,
            ),
        },
        "folds": fold_out,
        "track_wall": {"auto_bridge_to_a_track": False, "live_trading_trigger": False},
        "note_ko": "일자 부착 PoC — quad DOY interp 또는 OHLCV proxy. 승격·live 트리거 아님.",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(
        f"method={args.attachment_method} in_sample_gated={in_gated['price_directional_hit_rate']} "
        f"wf_gated_mean={out['blocked_walkforward_test_only']['perdate_regime_gated']['mean_test_accuracy']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
