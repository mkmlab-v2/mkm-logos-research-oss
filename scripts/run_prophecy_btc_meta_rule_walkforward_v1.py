#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_btc_h2_nb12p0_ssot_latest.json"
DEFAULT_BTC_CSV = ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "prophecy_btc_meta_rule_walkforward_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_btc_features(csv_path: Path) -> dict[str, dict[str, float]]:
    rows: list[tuple[str, float]] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f)
        for r in rd:
            rows.append((str(r["Date"]), float(r["Close"])))
    rows.sort(key=lambda x: x[0])
    dates = [d for d, _ in rows]
    closes = [c for _, c in rows]

    feats: dict[str, dict[str, float]] = {}
    for i in range(1, len(rows)):
        d = dates[i]
        c0 = closes[i - 1]
        if c0 == 0:
            continue
        ret1 = (closes[i] - c0) / c0
        ret3 = 0.0
        if i >= 3 and closes[i - 3] != 0:
            ret3 = (closes[i - 1] - closes[i - 3]) / closes[i - 3]
        vals: list[float] = []
        for j in range(max(1, i - 9), i + 1):
            p0 = closes[j - 1]
            p1 = closes[j]
            if p0 != 0:
                vals.append(abs((p1 - p0) / p0))
        vol10 = (sum(vals) / len(vals)) if vals else 0.0
        feats[d] = {"ret1": ret1, "ret3": ret3, "vol10": vol10}
    return feats


def _regime_keys(feats: dict[str, dict[str, float]], dates: list[str]) -> dict[str, str]:
    vol_series = [float((feats.get(d) or {}).get("vol10", 0.0)) for d in dates]
    s = sorted(vol_series)
    if not s:
        return {d: "mid_flat" for d in dates}
    q1 = s[len(s) // 3]
    q2 = s[(2 * len(s)) // 3]
    out: dict[str, str] = {}
    for d in dates:
        f = feats.get(d) or {}
        vol = float(f.get("vol10", 0.0))
        t = float(f.get("ret3", 0.0))
        vol_tag = "low" if vol <= q1 else ("high" if vol >= q2 else "mid")
        trend_tag = "up" if t > 0 else ("down" if t < 0 else "flat")
        out[d] = f"{vol_tag}_{trend_tag}"
    return out


def _apply_rule(pred: str, rule: str) -> str:
    p = str(pred or "").lower()
    if p not in ("bull", "bear", "neutral"):
        p = "neutral"
    if rule == "follow":
        return p
    if rule == "invert":
        return "bear" if p == "bull" else ("bull" if p == "bear" else "neutral")
    if rule == "neutralize":
        return "neutral"
    if rule == "always_bull":
        return "bull"
    if rule == "always_bear":
        return "bear"
    return p


def _blocked_folds(dates: list[str], n_folds: int) -> list[tuple[list[str], list[str]]]:
    n = len(dates)
    base = n // n_folds
    rem = n % n_folds
    blocks: list[list[str]] = []
    i = 0
    for b in range(n_folds):
        sz = base + (1 if b < rem else 0)
        blocks.append(dates[i : i + sz])
        i += sz
    out: list[tuple[list[str], list[str]]] = []
    for f in range(1, n_folds):
        tr: list[str] = []
        for b in range(f):
            tr.extend(blocks[b])
        te = blocks[f]
        if tr and te:
            out.append((tr, te))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="BTC meta-rule regime walkforward (research only).")
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC_CSV)
    ap.add_argument("--n-folds", type=int, default=4)
    ap.add_argument("--min-samples-per-regime", type=int, default=20)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = _load_json(args.score_json)
    rows = [r for r in (doc.get("rows") or []) if isinstance(r, dict) and str(r.get("instrument") or "").lower() == "btc"]
    if not rows:
        raise SystemExit("no btc rows")
    rows.sort(key=lambda r: str(r.get("eval_date") or ""))
    dates = sorted({str(r.get("eval_date") or "")[:10] for r in rows})
    by_date = {str(r.get("eval_date") or "")[:10]: r for r in rows}

    feats = _load_btc_features(args.btc_csv)
    regime = _regime_keys(feats, dates)
    folds = _blocked_folds(dates, max(2, int(args.n_folds)))

    candidate_rules = ["follow", "invert", "neutralize", "always_bull", "always_bear"]
    fold_out: list[dict[str, Any]] = []
    test_accs: list[float] = []
    beat_flags: list[bool] = []

    for fi, (train_dates, test_dates) in enumerate(folds):
        regime_rule: dict[str, str] = {}
        global_hits: dict[str, int] = {k: 0 for k in candidate_rules}
        global_n = 0
        for d in train_dates:
            r = by_date.get(d)
            if not r:
                continue
            pred = str(r.get("predicted_direction") or "neutral").lower()
            act = str(r.get("actual_direction") or "neutral").lower()
            for rule in candidate_rules:
                if _apply_rule(pred, rule) == act:
                    global_hits[rule] += 1
            global_n += 1
        best_global = max(candidate_rules, key=lambda k: (global_hits[k] / global_n) if global_n else -1.0)

        groups: dict[str, list[dict[str, Any]]] = {}
        for d in train_dates:
            if d in by_date:
                groups.setdefault(regime.get(d, "mid_flat"), []).append(by_date[d])

        for rg, rs in groups.items():
            if len(rs) < int(args.min_samples_per_regime):
                regime_rule[rg] = best_global
                continue
            hits = {k: 0 for k in candidate_rules}
            for rr in rs:
                pred = str(rr.get("predicted_direction") or "neutral").lower()
                act = str(rr.get("actual_direction") or "neutral").lower()
                for rule in candidate_rules:
                    if _apply_rule(pred, rule) == act:
                        hits[rule] += 1
            best = max(candidate_rules, key=lambda k: hits[k] / len(rs))
            regime_rule[rg] = best

        train_h = 0
        for d in train_dates:
            r = by_date.get(d)
            if not r:
                continue
            rg = regime.get(d, "mid_flat")
            rule = regime_rule.get(rg, best_global)
            if _apply_rule(str(r.get("predicted_direction") or "neutral"), rule) == str(r.get("actual_direction") or "neutral"):
                train_h += 1
        train_acc = (train_h / len(train_dates)) if train_dates else 0.0

        test_h = 0
        bull_n = 0
        for d in test_dates:
            r = by_date.get(d)
            if not r:
                continue
            rg = regime.get(d, "mid_flat")
            rule = regime_rule.get(rg, best_global)
            pred2 = _apply_rule(str(r.get("predicted_direction") or "neutral"), rule)
            act = str(r.get("actual_direction") or "neutral")
            if pred2 == act:
                test_h += 1
            if act == "bull":
                bull_n += 1
        n_test = len(test_dates)
        test_acc = (test_h / n_test) if n_test else 0.0
        bull_rate = (bull_n / n_test) if n_test else 0.0
        beats = test_acc > bull_rate
        test_accs.append(test_acc)
        beat_flags.append(beats)

        fold_out.append(
            {
                "fold_index": fi,
                "train_dates": train_dates,
                "test_dates": test_dates,
                "n_train_rows": len(train_dates),
                "n_test_rows": len(test_dates),
                "best_params_from_train": {"meta_rule": "regime_rule_select_v1", "best_global_rule": best_global},
                "train": {"accuracy": round(train_acc, 6), "hits": train_h, "n": len(train_dates)},
                "test": {"accuracy": round(test_acc, 6), "hits": test_h, "n": n_test, "always_bull_control": round(bull_rate, 6)},
                "test_beats_always_bull": beats,
            }
        )

    mean_test = (sum(test_accs) / len(test_accs)) if test_accs else 0.0
    var = (sum((x - mean_test) ** 2 for x in test_accs) / len(test_accs)) if test_accs else 0.0
    stdev = math.sqrt(var) if test_accs else 0.0

    out = {
        "schema": "prophecy_per_date_combo_walkforward_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {
            "score_json": str(args.score_json),
            "btc_csv": str(args.btc_csv),
            "target_instrument": "btc",
            "train_objective": "meta_regime_rule_accuracy",
            "n_rows_after_target_filter": len(rows),
            "n_folds": int(args.n_folds),
            "n_folds_requested": int(args.n_folds),
            "n_folds_effective": int(args.n_folds),
            "n_folds_clamped": False,
            "n_distinct_eval_dates": len(dates),
            "n_walkforward_folds": len(folds),
            "note": "Blocked walk-forward with per-regime rule selection on source prediction.",
        },
        "folds": fold_out,
        "aggregate": {
            "mean_test_accuracy": round(mean_test, 6),
            "stdev_test_accuracy": round(stdev, 6),
            "min_test_accuracy": round(min(test_accs), 6) if test_accs else None,
            "max_test_accuracy": round(max(test_accs), 6) if test_accs else None,
            "fraction_test_beats_always_bull": round(sum(1 for x in beat_flags if x) / len(beat_flags), 6) if beat_flags else None,
        },
        "note": "Meta-rule regime selection baseline candidate.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(
        f"folds={len(fold_out)} mean_test_acc={out['aggregate']['mean_test_accuracy']} "
        f"stdev={out['aggregate']['stdev_test_accuracy']} beat_bull_frac={out['aggregate']['fraction_test_beats_always_bull']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

