# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.85, L:0.8, K:0.45, M:0.3}
# Balance: 90
# Purpose: Activation-focused combo spike for per-row prediction changes
# Keywords: prophecy, activation, combo, delta, btrack, research
#!/usr/bin/env python3
"""Activation-focused combo spike on btrack prophecy panel.

Goal: verify we can produce *material per-row prediction movement* (e.g. >=20 rows changed)
before trying fine-grained optimization. This is B-track research-only output.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_latest.json"
DEFAULT_KOSPI_CSV = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
DEFAULT_BTC_CSV = ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "prophecy_activation_combo_spike_v1_latest.json"
SCHEMA = "prophecy_activation_combo_spike_v1"
VALID = {"bull", "bear", "neutral"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _prior_completed_daily_return_by_eval_date(csv_path: Path) -> dict[str, float]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.logos_shadow_eval_lib import load_kospi_yf_rows

    rows = load_kospi_yf_rows(csv_path)
    if len(rows) < 3:
        return {}
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


def _dir_from_return(x: float, neutral_bps: float) -> str:
    thr = float(neutral_bps) / 10000.0
    if abs(x) < thr:
        return "neutral"
    return "bull" if x > 0 else "bear"


def _metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = 0
    hit = 0
    for r in rows:
        p = str(r.get("predicted_direction") or "").strip().lower()
        a = str(r.get("actual_direction") or "").strip().lower()
        if p not in VALID or a not in VALID:
            continue
        n += 1
        if p == a:
            hit += 1
    return {"price_directional_hit_rate": round(hit / n, 6) if n else None, "n_evaluated": n, "price_hits": hit}


def _apply_const(rows: list[dict[str, Any]], sign: str) -> tuple[list[dict[str, Any]], int]:
    out: list[dict[str, Any]] = []
    changed = 0
    for r in rows:
        nr = dict(r)
        old = str(nr.get("predicted_direction") or "").strip().lower()
        if old != sign:
            changed += 1
        nr["predicted_direction"] = sign
        out.append(nr)
    return out, changed


def _apply_prior_sign(
    rows: list[dict[str, Any]],
    *,
    kmap: dict[str, float],
    bmap: dict[str, float],
    neutral_bps: float,
) -> tuple[list[dict[str, Any]], int, int]:
    out: list[dict[str, Any]] = []
    changed = 0
    missing = 0
    for r in rows:
        nr = dict(r)
        inst = str(nr.get("instrument") or "").strip().lower()
        ed = str(nr.get("eval_date") or "").strip()[:10]
        mp = kmap if inst == "kospi" else bmap
        pr = mp.get(ed)
        if pr is None:
            missing += 1
            out.append(nr)
            continue
        sign = _dir_from_return(pr, neutral_bps)
        old = str(nr.get("predicted_direction") or "").strip().lower()
        if sign != old:
            changed += 1
        nr["predicted_direction"] = sign
        out.append(nr)
    return out, changed, missing


def main() -> int:
    ap = argparse.ArgumentParser(description="Activation combo spike (B-track).")
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI_CSV)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC_CSV)
    ap.add_argument("--min-activation-changes", type=int, default=20)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = _load_json(args.score_json)
    if not doc or not isinstance(doc.get("rows"), list):
        raise SystemExit(f"invalid score json: {args.score_json}")
    rows = [r for r in doc["rows"] if isinstance(r, dict)]
    neutral_bps = float(doc.get("neutral_bps") or 2.0)
    base = _metrics(rows)
    base_rate = float(base["price_directional_hit_rate"] or 0.0)

    kmap = _prior_completed_daily_return_by_eval_date(args.kospi_csv) if args.kospi_csv.is_file() else {}
    bmap = _prior_completed_daily_return_by_eval_date(args.btc_csv) if args.btc_csv.is_file() else {}

    lanes: list[dict[str, Any]] = []

    bull_rows, bull_changed = _apply_const(rows, "bull")
    bull_metrics = _metrics(bull_rows)
    lanes.append(
        {
            "lane_id": "always_bull_control",
            "changed_rows": bull_changed,
            "metrics": bull_metrics,
            "delta_vs_baseline": round(float(bull_metrics["price_directional_hit_rate"] or 0.0) - base_rate, 6),
            "activation_met": bull_changed >= args.min_activation_changes,
        }
    )

    bear_rows, bear_changed = _apply_const(rows, "bear")
    bear_metrics = _metrics(bear_rows)
    lanes.append(
        {
            "lane_id": "always_bear_control",
            "changed_rows": bear_changed,
            "metrics": bear_metrics,
            "delta_vs_baseline": round(float(bear_metrics["price_directional_hit_rate"] or 0.0) - base_rate, 6),
            "activation_met": bear_changed >= args.min_activation_changes,
        }
    )

    prior_rows, prior_changed, prior_missing = _apply_prior_sign(rows, kmap=kmap, bmap=bmap, neutral_bps=neutral_bps)
    prior_metrics = _metrics(prior_rows)
    lanes.append(
        {
            "lane_id": "prior_completed_return_sign_v1",
            "changed_rows": prior_changed,
            "missing_prior_rows": prior_missing,
            "metrics": prior_metrics,
            "delta_vs_baseline": round(float(prior_metrics["price_directional_hit_rate"] or 0.0) - base_rate, 6),
            "activation_met": prior_changed >= args.min_activation_changes,
            "note": "Causal prior return sign per instrument/date; no same-day lookahead.",
        }
    )

    best = sorted(lanes, key=lambda x: x["metrics"].get("price_directional_hit_rate") or -1.0, reverse=True)[0]
    out = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {
            "score_json": str(args.score_json),
            "kospi_csv": str(args.kospi_csv),
            "btc_csv": str(args.btc_csv),
            "min_activation_changes": args.min_activation_changes,
        },
        "baseline": {"lane_id": "baseline", "metrics": base},
        "lanes": lanes,
        "best_lane_by_hit_rate": best,
        "summary": {
            "activation_target_changes": args.min_activation_changes,
            "lanes_meeting_activation": [x["lane_id"] for x in lanes if x.get("activation_met")],
        },
        "note": "Activation-first probe. Control lanes are not deployable policies; used to size headroom and calibration gaps.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(
        f"BASE {base['price_directional_hit_rate']} | BEST {best['lane_id']} "
        f"{best['metrics'].get('price_directional_hit_rate')} chg={best.get('changed_rows')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
