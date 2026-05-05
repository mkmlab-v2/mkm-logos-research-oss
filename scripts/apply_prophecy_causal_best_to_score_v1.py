#!/usr/bin/env python3
"""Apply causal sweep best thresholds to btrack prophecy score rows in-place."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_latest.json"
DEFAULT_SWEEP = ROOT / "docs" / "final" / "artifacts" / "prophecy_causal_threshold_sweep_v1_latest.json"
DEFAULT_KOSPI_CSV = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
DEFAULT_BTC_CSV = ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"
DEFAULT_REPORT = ROOT / "docs" / "final" / "artifacts" / "prophecy_causal_active_apply_latest.json"
DEFAULT_BACKUP = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_pre_causal_active_latest.json"
VALID = {"bull", "bear", "neutral"}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


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


def _pred_from_prior(prior_ret: float | None, low_thr: float, high_thr: float, old_pred: str) -> str:
    if prior_ret is None:
        return old_pred if old_pred in VALID else "neutral"
    if prior_ret <= low_thr:
        return "bear"
    if prior_ret >= high_thr:
        return "bull"
    return "neutral"


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply causal sweep best thresholds to score rows.")
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--sweep-json", type=Path, default=DEFAULT_SWEEP)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI_CSV)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC_CSV)
    ap.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--backup-out", type=Path, default=DEFAULT_BACKUP)
    args = ap.parse_args()

    score_path = args.score_json if args.score_json.is_absolute() else ROOT / args.score_json
    sweep_path = args.sweep_json if args.sweep_json.is_absolute() else ROOT / args.sweep_json
    report_path = args.report_out if args.report_out.is_absolute() else ROOT / args.report_out
    backup_path = args.backup_out if args.backup_out.is_absolute() else ROOT / args.backup_out

    score = _load(score_path)
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path.write_text(json.dumps(score, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sweep = _load(sweep_path)
    best = sweep.get("best_candidate") or {}
    low_thr = float(best.get("low_thr"))
    high_thr = float(best.get("high_thr"))

    rows = score.get("rows")
    if not isinstance(rows, list):
        raise SystemExit("score rows[] missing")

    km = _prior_completed_daily_return_by_eval_date(args.kospi_csv) if args.kospi_csv.is_file() else {}
    bm = _prior_completed_daily_return_by_eval_date(args.btc_csv) if args.btc_csv.is_file() else {}

    changed = 0
    missing_prior = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        inst = str(row.get("instrument") or "").strip().lower()
        ed = str(row.get("eval_date") or "").strip()[:10]
        mp = km if inst == "kospi" else bm
        pr = mp.get(ed)
        old = str(row.get("predicted_direction") or "").strip().lower()
        new = _pred_from_prior(pr, low_thr=low_thr, high_thr=high_thr, old_pred=old)
        if pr is None:
            missing_prior += 1
        if new != old:
            changed += 1
        row["predicted_direction"] = new
        row["causal_active_threshold_low"] = low_thr
        row["causal_active_threshold_high"] = high_thr

    score.setdefault("meta", {})
    if isinstance(score["meta"], dict):
        score["meta"]["causal_active_applied"] = True
        score["meta"]["causal_active_threshold_low"] = low_thr
        score["meta"]["causal_active_threshold_high"] = high_thr
        score["meta"]["causal_active_applied_at_utc"] = _now()

    score_path.write_text(json.dumps(score, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = {
        "schema": "prophecy_causal_active_apply_v1",
        "generated_at_utc": _now(),
        "score_json": str(score_path),
        "backup_score_json": str(backup_path),
        "sweep_json": str(sweep_path),
        "applied_low_thr": low_thr,
        "applied_high_thr": high_thr,
        "changed_rows": changed,
        "missing_prior_rows": missing_prior,
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE: {score_path.resolve()}")
    print(f"WROTE: {backup_path.resolve()}")
    print(f"WROTE: {report_path.resolve()}")
    print(f"changed_rows={changed} missing_prior_rows={missing_prior} low={low_thr} high={high_thr}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
