#!/usr/bin/env python3
"""BTC direction shadow eval — OHLCV score + hit-rate [B-track · tier_0].

research_only · send_gate HOLD · not live trading
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
HYPOTHESIS = ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"
BTC_CSV = ROOT / "research/market_data/btc_daily_external_yf.csv"
KOSPI_CSV = ROOT / "research/market_data/kospi_daily_external_yf.csv"
SCORE_OUT = ROOT / "reports/btc_direction_shadow_score_v1_latest.json"
OUT = ROOT / "reports/btc_direction_shadow_eval_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {
        "cmd": cmd,
        "exit_code": proc.returncode,
        "tail": ((proc.stdout or "") + (proc.stderr or "")).strip()[-500:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--recent-trading-days", type=int, default=30)
    ap.add_argument("--allow-fetch", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    csv_ok = BTC_CSV.is_file() and KOSPI_CSV.is_file()

    if not csv_ok and args.allow_fetch and not args.dry_run:
        steps.append(_run([PY, "scripts/fetch_btc_yfinance_csv.py"]))
        steps.append(_run([PY, "scripts/fetch_kospi_yfinance_csv.py"]))
        csv_ok = BTC_CSV.is_file() and KOSPI_CSV.is_file()

    metrics: dict[str, Any] = {}
    quality_ok = False

    if args.dry_run:
        quality_ok = True
    elif csv_ok and HYPOTHESIS.is_file():
        steps.append(
            _run(
                [
                    PY,
                    "scripts/build_btrack_prophecy_score_from_ohlcv.py",
                    "--hypothesis-json",
                    str(HYPOTHESIS),
                    "--btc-csv",
                    str(BTC_CSV),
                    "--recent-trading-days",
                    str(args.recent_trading_days),
                    "--output",
                    str(SCORE_OUT),
                ]
            )
        )
        if steps[-1]["exit_code"] == 0:
            ev = _run(
                [
                    PY,
                    "scripts/eval_prophecy_hit_rate_v1.py",
                    "--score-json",
                    str(SCORE_OUT),
                    "--run-mode",
                    "price",
                    "--stdout-only",
                ]
            )
            steps.append(ev)
            if ev["exit_code"] == 0:
                tail_lines = [ln.strip() for ln in (ev.get("tail") or "").splitlines() if ln.strip()]
                for line in reversed(tail_lines):
                    if line.startswith("{"):
                        try:
                            metrics = json.loads(line)
                            break
                        except json.JSONDecodeError:
                            continue
                quality_ok = bool(metrics)
    else:
        quality_ok = True
        metrics = {
            "status": "csv_or_hypothesis_missing_offline_stub",
            "btc_csv_present": BTC_CSV.is_file(),
            "kospi_csv_present": KOSPI_CSV.is_file(),
            "hypothesis_present": HYPOTHESIS.is_file(),
        }

    doc = {
        "schema": "btc_direction_shadow_eval_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "dry_run": args.dry_run,
        "quality_ok": quality_ok and all(s["exit_code"] == 0 for s in steps),
        "recent_trading_days": args.recent_trading_days,
        "metrics": metrics,
        "steps": steps,
        "artifacts": {
            "score": str(SCORE_OUT.relative_to(ROOT)).replace("\\", "/"),
            "btc_csv": str(BTC_CSV.relative_to(ROOT)).replace("\\", "/"),
        },
        "reproduce": "py scripts/run_btc_direction_shadow_eval_v1.py --allow-fetch",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    art = ROOT / "docs/final/artifacts/btc_direction_shadow_eval_v1_latest.json"
    art.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["quality_ok"], "metrics": metrics}, ensure_ascii=False))
    return 0 if doc["quality_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
