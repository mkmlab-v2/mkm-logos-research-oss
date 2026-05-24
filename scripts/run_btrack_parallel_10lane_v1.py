#!/usr/bin/env python3
"""[HYPO] 10-lane B-track parallel run — KOSPI/BTC split, no Track A promotion."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/btrack_parallel_10lane_v1_latest.json"
BTC_CSV = ROOT / "research/market_data/btc_daily_external_yf.csv"
KOSPI_CSV = ROOT / "research/market_data/kospi_daily_external_yf.csv"
HYP = ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"
KOSPI_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_kospi_30d_dual_parallel_v1.json"
KOSPI_EVAL = ROOT / "reports/prophecy_hit_rate_eval_kospi_30d_dual_parallel_v1_latest.json"
BTC_EVAL = ROOT / "reports/prophecy_hit_rate_eval_btc_30d_dual_parallel_v1_latest.json"
BTC_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
SIDECAR = ROOT / "docs/final/artifacts/btrack_prophecy_score_insight_sidecar_v1_latest.json"
COMBO_OUT = ROOT / "reports/prophecy_lens_combo_backtest_30d_logos_omit_v1.json"
ANCHOR_SCORE = ROOT / "reports/btrack_prophecy_score_30d_frozen_kpi_a_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(p)


def _run_lane(lane_id: str, steps: list[list[str]]) -> dict[str, Any]:
    py = sys.executable
    tails: list[str] = []
    for cmd in steps:
        full = [py, *cmd[1:]] if cmd and cmd[0] == "PY" else list(cmd)
        cp = subprocess.run(full, cwd=str(ROOT), capture_output=True, text=True)
        tail = (cp.stdout or cp.stderr or "").strip()[-400:]
        tails.append(tail)
        if cp.returncode != 0:
            return {
                "lane": lane_id,
                "ok": False,
                "exit_code": cp.returncode,
                "failed_step": " ".join(full[:4]),
                "tail": tail,
            }
    return {"lane": lane_id, "ok": True, "exit_code": 0, "tail": tails[-1] if tails else ""}


def _lane_market_data() -> dict[str, Any]:
    return _run_lane(
        "market_data",
        [
            ["PY", "scripts/fetch_kospi_yfinance_csv.py"],
            ["PY", "scripts/fetch_btc_yfinance_csv.py"],
        ],
    )


def _lane_lens_coverage() -> dict[str, Any]:
    return _run_lane("parallel_lens_coverage", [["PY", "scripts/run_btrack_parallel_lens_coverage_v1.py"]])


def _lane_hybrid() -> dict[str, Any]:
    return _run_lane(
        "v1_ms_hybrid",
        [["PY", "scripts/run_btrack_v1_ms_hybrid_parallel_v1.py", "--max-workers", "5"]],
    )


def _lane_logos_off() -> dict[str, Any]:
    return _run_lane("logos_off_perdate", [["PY", "scripts/_parallel_prophecy_logos_off_perdate_v1.py"]])


def _lane_combo() -> dict[str, Any]:
    return _run_lane(
        "combo_backtest",
        [
            [
                "PY",
                "scripts/run_prophecy_lens_combo_backtest_v1.py",
                "--score-json",
                _rel(ANCHOR_SCORE),
                "--sidecar-json",
                _rel(SIDECAR),
                "--target-instrument",
                "btc",
                "--logos-vote-mode",
                "omit",
                "--output",
                _rel(COMBO_OUT),
            ]
        ],
    )


def _lane_pytest() -> dict[str, Any]:
    return _run_lane(
        "pytest",
        [["PY", "-m", "pytest", "tests/test_run_prophecy_lens_combo_logos_vote_mode_v1.py", "-q"]],
    )


def _lane_kospi_30d() -> dict[str, Any]:
    return _run_lane(
        "kospi_30d",
        [
            [
                "PY",
                "scripts/generate_btrack_hypothesis_prophecy_v1.py",
                "--research-evaluation-instrument",
                "kospi",
            ],
            [
                "PY",
                "scripts/build_btrack_prophecy_score_from_ohlcv.py",
                "--recent-trading-days",
                "30",
                "--force-dual-leg-panel",
                "--kospi-csv",
                _rel(KOSPI_CSV),
                "--btc-csv",
                _rel(BTC_CSV),
                "--hypothesis-json",
                _rel(HYP),
                "--output",
                _rel(KOSPI_SCORE),
            ],
            [
                "PY",
                "scripts/eval_prophecy_hit_rate_v1.py",
                "--run-mode",
                "price",
                "--score-json",
                _rel(KOSPI_SCORE),
                "--headline-instrument",
                "kospi",
                "--output",
                _rel(KOSPI_EVAL),
            ],
            [
                "PY",
                "scripts/run_prophecy_instrument_combo_walkforward_v1.py",
                "--score-json",
                _rel(KOSPI_SCORE),
                "--kospi-csv",
                _rel(KOSPI_CSV),
                "--btc-csv",
                _rel(BTC_CSV),
                "--output",
                "reports/prophecy_instrument_combo_wf_kospi_30d_parallel_v1_latest.json",
            ],
        ],
    )


def _lane_logos_revalidation() -> dict[str, Any]:
    return _run_lane(
        "logos_revalidation",
        [
            [
                "PY",
                "scripts/run_prophecy_logos_revalidation_suite_v1.py",
                "--score-json",
                _rel(KOSPI_SCORE),
                "--sidecar-json",
                _rel(SIDECAR),
                "--target-instrument",
                "kospi",
            ]
        ],
    )


def _lane_btc_30d_daily() -> dict[str, Any]:
    return _run_lane(
        "btc_30d_daily",
        [
            [
                "PY",
                "scripts/generate_btrack_hypothesis_prophecy_v1.py",
                "--research-evaluation-instrument",
                "btc",
            ],
            [
                "PY",
                "scripts/build_btrack_prophecy_score_from_ohlcv.py",
                "--recent-trading-days",
                "30",
                "--force-dual-leg-panel",
                "--btc-csv",
                _rel(BTC_CSV),
                "--kospi-csv",
                _rel(KOSPI_CSV),
                "--hypothesis-json",
                _rel(HYP),
                "--output",
                _rel(BTC_SCORE),
            ],
            [
                "PY",
                "scripts/eval_prophecy_hit_rate_v1.py",
                "--run-mode",
                "price",
                "--score-json",
                _rel(BTC_SCORE),
                "--headline-instrument",
                "btc",
                "--output",
                _rel(BTC_EVAL),
            ],
            [
                "PY",
                "scripts/check_btrack_prophecy_chain_prereqs_v1.py",
                "--stdout-only",
            ],
        ],
    )


def _lane_weekly_pack() -> dict[str, Any]:
    return _run_lane("weekly_pack", [["PY", "scripts/run_btrack_weekly_prophecy_review_pack_v1.py"]])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-workers", type=int, default=6)
    ap.add_argument("--skip-weekly", action="store_true", help="Skip weekly pack (combo backtest refresh).")
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()

    phase_a = [
        ("market_data", _lane_market_data),
        ("parallel_lens_coverage", _lane_lens_coverage),
        ("v1_ms_hybrid", _lane_hybrid),
        ("logos_off_perdate", _lane_logos_off),
        ("combo_backtest", _lane_combo),
        ("pytest", _lane_pytest),
    ]
    if not args.skip_weekly:
        phase_a.append(("weekly_pack", _lane_weekly_pack))

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.max_workers)) as pool:
        futs = {pool.submit(fn): lid for lid, fn in phase_a}
        for fut in as_completed(futs):
            results.append(fut.result())

    kospi_res = _lane_kospi_30d()
    results.append(kospi_res)
    if kospi_res.get("ok"):
        results.append(_lane_logos_revalidation())
    else:
        results.append(
            {
                "lane": "logos_revalidation",
                "ok": False,
                "skipped": True,
                "reason": "kospi_30d failed",
            }
        )

    results.append(_lane_btc_30d_daily())

    subprocess.run(
        [sys.executable, "scripts/build_btrack_parallel_run_summary_v1.py"],
        cwd=str(ROOT),
        check=False,
    )
    subprocess.run(
        [sys.executable, "scripts/build_btrack_parallel_weekly_fusion_v1.py"],
        cwd=str(ROOT),
        check=False,
    )

    pack = {
        "schema": "btrack_parallel_10lane_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "max_workers": args.max_workers,
        "lanes": sorted(results, key=lambda r: str(r.get("lane"))),
        "all_ok": all(r.get("ok") for r in results),
        "failed": [r["lane"] for r in results if not r.get("ok")],
        "fusion": {
            "summary": "reports/btrack_parallel_run_summary_v1_latest.json",
            "weekly_fusion": "reports/btrack_parallel_weekly_fusion_v1_latest.json",
        },
        "track_a_live_promotion": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": pack["all_ok"], "output": str(args.output), "failed": pack["failed"]}, ensure_ascii=False))
    return 0 if pack["all_ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
