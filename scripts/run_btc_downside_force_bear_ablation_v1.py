#!/usr/bin/env python3
"""[HYPO] AB: mild downside_force_bear ON vs OFF — in-sample BTC acc + lens WF mean."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/build_btrack_prophecy_score_from_ohlcv.py"
LENS_WF = ROOT / "scripts/run_prophecy_per_date_combo_walkforward_v1.py"
DUAL = ROOT / "scripts/build_btrack_dual_per_date_directions_v1.py"
HYPO = ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"
BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
WORK = ROOT / "reports/_btc_downside_force_bear_ablation_work"
DEFAULT_OUT = ROOT / "reports/btc_downside_force_bear_ablation_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> int:
    return subprocess.run(cmd, cwd=str(ROOT), check=False).returncode


def _btc_acc(score_path: Path) -> float | None:
    doc = json.loads(score_path.read_text(encoding="utf-8-sig"))
    rows = [r for r in (doc.get("rows") or []) if str(r.get("instrument")).lower() == "btc"]
    if not rows:
        return None
    hits = sum(1 for r in rows if r.get("predicted_direction") == r.get("actual_direction"))
    return round(hits / len(rows), 6)


def _lens_mean(wf_path: Path) -> float | None:
    doc = json.loads(wf_path.read_text(encoding="utf-8-sig"))
    agg = doc.get("aggregate") if isinstance(doc.get("aggregate"), dict) else {}
    v = agg.get("mean_test_accuracy")
    return float(v) if isinstance(v, (int, float)) else None


def _one_variant(
    slug: str,
    *,
    downside_on: bool,
    recent_days: int,
    neutral_bps: float,
    per_date_json: Path,
) -> dict[str, Any]:
    WORK.mkdir(parents=True, exist_ok=True)
    score_out = WORK / f"score_{slug}.json"
    wf_out = WORK / f"lens_wf_{slug}.json"
    build_cmd: list[str] = [
        sys.executable,
        str(BUILD),
        "--hypothesis-json",
        str(HYPO),
        "--btc-csv",
        str(BTC),
        "--force-dual-leg-panel",
        "--recent-trading-days",
        str(recent_days),
        "--neutral-bps",
        str(neutral_bps),
        "--per-date-direction-json",
        str(per_date_json),
        "--output",
        str(score_out),
    ]
    if downside_on:
        build_cmd.extend(
            [
                "--downside-force-bear-enable",
                "--downside-force-bear-lookback",
                "5",
                "--downside-force-bear-min-down-days",
                "3",
                "--downside-force-bear-min-cum-down-pct",
                "4.5",
            ]
        )
    rc_b = _run(build_cmd)
    row: dict[str, Any] = {"slug": slug, "downside_force_bear": downside_on, "build_exit": rc_b}
    if rc_b != 0:
        row["error"] = "build_failed"
        return row
    row["btc_in_sample_accuracy"] = _btc_acc(score_out)
    wf_cmd = [
        sys.executable,
        str(LENS_WF),
        "--score-json",
        str(score_out),
        "--btc-csv",
        str(BTC),
        "--target-instrument",
        "btc",
        "--train-objective",
        "margin_vs_bull",
        "--n-folds",
        "6",
        "--output",
        str(wf_out),
    ]
    rc_w = _run(wf_cmd)
    row["lens_wf_exit"] = rc_w
    if rc_w == 0:
        row["lens_wf_mean_test_accuracy"] = _lens_mean(wf_out)
        row["lens_wf_json"] = str(wf_out.relative_to(ROOT)).replace("\\", "/")
    row["score_json"] = str(score_out.relative_to(ROOT)).replace("\\", "/")
    return row


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--recent-trading-days", type=int, default=180)
    ap.add_argument("--neutral-bps", type=float, default=2.0)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    per_date = ROOT / "reports" / "btrack_ensemble_per_date_directions_dual_v1_latest.json"
    ens_rc = _run(
        [
            sys.executable,
            str(DUAL),
            "--recent-trading-days",
            str(int(args.recent_trading_days)),
            "--btc-csv",
            str(BTC),
            "--dual-output",
            str(per_date),
        ]
    )
    if ens_rc != 0:
        return ens_rc

    variants = [
        _one_variant(
            "downside_on",
            downside_on=True,
            recent_days=int(args.recent_trading_days),
            neutral_bps=float(args.neutral_bps),
            per_date_json=per_date,
        ),
        _one_variant(
            "downside_off",
            downside_on=False,
            recent_days=int(args.recent_trading_days),
            neutral_bps=float(args.neutral_bps),
            per_date_json=per_date,
        ),
    ]
    on = next((v for v in variants if v.get("slug") == "downside_on"), {})
    off = next((v for v in variants if v.get("slug") == "downside_off"), {})
    delta_acc = None
    delta_wf = None
    if isinstance(on.get("btc_in_sample_accuracy"), (int, float)) and isinstance(
        off.get("btc_in_sample_accuracy"), (int, float)
    ):
        delta_acc = round(float(on["btc_in_sample_accuracy"]) - float(off["btc_in_sample_accuracy"]), 6)
    if isinstance(on.get("lens_wf_mean_test_accuracy"), (int, float)) and isinstance(
        off.get("lens_wf_mean_test_accuracy"), (int, float)
    ):
        delta_wf = round(float(on["lens_wf_mean_test_accuracy"]) - float(off["lens_wf_mean_test_accuracy"]), 6)

    doc = {
        "schema": "btc_downside_force_bear_ablation_v1",
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "generated_at_utc": _utc_now(),
        "recent_trading_days": int(args.recent_trading_days),
        "neutral_bps": float(args.neutral_bps),
        "variants": variants,
        "delta_on_minus_off": {
            "btc_in_sample_accuracy": delta_acc,
            "lens_wf_mean_test_accuracy": delta_wf,
        },
    }
    out = args.output if args.output.is_absolute() else ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out} delta_wf={delta_wf} delta_btc_acc={delta_acc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
