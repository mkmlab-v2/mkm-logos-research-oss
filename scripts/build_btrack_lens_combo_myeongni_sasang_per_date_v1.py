#!/usr/bin/env python3
"""[HYPO] Per-date BTC directions from myeongni+sasang majority (lens combo harness)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_prophecy_lens_combo_backtest_v1 import (  # noqa: E402
    _extract_lens_maps,
    _majority_sign,
    _read_json,
    _sign_to_dir,
)

DEFAULT_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_30d_latest.json"
DEFAULT_SIDECAR = ROOT / "docs/final/artifacts/btrack_prophecy_score_insight_sidecar_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_lens_combo_ms_per_date_v1_latest.json"
DEFAULT_REPORT = ROOT / "reports/btrack_lens_combo_ms_per_date_chain_v1_latest.json"
BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_rows(*, score_json: Path, sidecar_json: Path) -> list[dict[str, object]]:
    score = _read_json(score_json)
    sidecar = _read_json(sidecar_json)
    my_map, sa_map, _logos, _logos_conf = _extract_lens_maps(sidecar)
    dates = sorted(
        {
            str(r.get("eval_date") or "")[:10]
            for r in score.get("rows") or []
            if isinstance(r, dict)
            and str(r.get("instrument") or "").strip().lower() == "btc"
        }
    )
    dates = [d for d in dates if d]
    rows: list[dict[str, object]] = []
    for ed in dates:
        signs = [int(my_map.get(ed, 0)), int(sa_map.get(ed, 0))]
        pos = _majority_sign(signs)
        rows.append(
            {
                "eval_date": ed,
                "instrument": "btc",
                "predicted_direction": _sign_to_dir(pos),
                "ensemble_mode": "lens_combo_myeongni_sasang_v1",
                "lens_signs": {"myeongni": signs[0], "sasang": signs[1]},
            }
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--sidecar-json", type=Path, default=DEFAULT_SIDECAR)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--run-score-eval", action="store_true")
    ap.add_argument("--report-json", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--recent-trading-days", type=int, default=30)
    ap.add_argument(
        "--btc-only-score",
        action="store_true",
        help="Single-leg BTC score (no dual-leg panel); eval uses --headline-instrument btc.",
    )
    args = ap.parse_args(argv)

    if not args.score_json.is_file() or not args.sidecar_json.is_file():
        print("Missing score or sidecar JSON.", file=sys.stderr)
        return 2

    rows = build_rows(score_json=args.score_json, sidecar_json=args.sidecar_json)
    doc = {
        "schema": "btrack_ensemble_per_date_directions_v1",
        "version": "1.0.0",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "ts_utc": _utc_now(),
        "ensemble_mode": "lens_combo_myeongni_sasang_v1",
        "research_only": True,
        "note": "Majority vote myeongni+sasang only; logos excluded. research_only.",
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()} rows={len(rows)}")

    if not args.run_score_eval:
        return 0

    work = ROOT / "reports/btrack_lens_combo_ms_per_date_work"
    work.mkdir(parents=True, exist_ok=True)
    score_out = work / "score.json"
    eval_out = work / "eval.json"
    score_cmd = [
        sys.executable,
        "scripts/build_btrack_prophecy_score_from_ohlcv.py",
        "--recent-trading-days",
        str(args.recent_trading_days),
        "--btc-csv",
        str(BTC),
        "--per-date-direction-json",
        str(args.output.relative_to(ROOT)),
        "--output",
        str(score_out.relative_to(ROOT)),
    ]
    if args.btc_only_score:
        score_cmd.extend(
            ["--hypothesis-json", "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"]
        )
    else:
        score_cmd.extend(["--force-dual-leg-panel", "--kospi-csv", str(KOSPI)])
    eval_cmd = [
        sys.executable,
        "scripts/eval_prophecy_hit_rate_v1.py",
        "--run-mode",
        "price",
        "--score-json",
        str(score_out.relative_to(ROOT)),
        "--output",
        str(eval_out.relative_to(ROOT)),
    ]
    if args.btc_only_score:
        eval_cmd.extend(["--headline-instrument", "btc"])
    steps = [score_cmd, eval_cmd]
    for cmd in steps:
        if subprocess.run(cmd, cwd=str(ROOT)).returncode != 0:
            return 1

    ev = json.loads(eval_out.read_text(encoding="utf-8"))
    m = ev.get("metrics") if isinstance(ev.get("metrics"), dict) else {}
    btc_rows = [r for r in json.loads(score_out.read_text())["rows"] if r.get("instrument") == "btc"]
    hits = sum(1 for r in btc_rows if r.get("predicted_direction") == r.get("actual_direction"))
    report = {
        "schema": "btrack_lens_combo_ms_per_date_chain_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "per_date_json": str(args.output.relative_to(ROOT)),
        "metrics_all_rows": m,
        "btc_only": {
            "price_directional_hit_rate": hits / len(btc_rows) if btc_rows else None,
            "n_evaluated": len(btc_rows),
            "price_hits": hits,
        },
    }
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.report_json.resolve()}")
    print(f"BTC only: {report['btc_only']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
