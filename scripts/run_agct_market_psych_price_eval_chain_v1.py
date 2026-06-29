#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AGCT DNA+market_psych: yfinance psych -> per-date fusion -> 30d price hit-rate eval."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_SUMMARY = ROOT / "reports/agct_market_psych_price_eval_chain_v1_latest.json"
ARTIFACT_SUMMARY = ROOT / "docs/final/artifacts/agct_market_psych_price_eval_chain_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> int:
    r = subprocess.run(cmd, cwd=str(ROOT))
    return int(r.returncode)


def _read_eval(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _hit(doc: dict[str, Any] | None) -> float | None:
    if not doc:
        return None
    return (doc.get("metrics") or {}).get("price_directional_hit_rate")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eval-days", type=int, default=30)
    ap.add_argument("--psych-days", type=int, default=60, help="yfinance rows to fetch (calendar)")
    ap.add_argument("--skip-yfinance", action="store_true")
    ap.add_argument("--tag", type=str, default="", help="Optional suffix for report paths.")
    ap.add_argument("--out-summary", type=Path, default=DEFAULT_SUMMARY)
    args = ap.parse_args()

    tag = f"_{args.tag}" if args.tag else ""
    psych_csv = ROOT / "data/market_sasang/market_psychology_kospi_from_yfinance_latest.csv"
    per_date = ROOT / f"reports/btrack_per_date_directions_agct_market_psych{tag}.json"
    score_json = ROOT / f"reports/btrack_prophecy_score_agct_market_psych{tag}.json"
    eval_kospi = ROOT / f"reports/prophecy_hit_rate_agct_market_psych{tag}_kospi.json"
    eval_btc = ROOT / f"reports/prophecy_hit_rate_agct_market_psych{tag}_btc.json"
    reasoning_out = ROOT / f"reports/sasang_dna_market_reasoning_kospi_eval{tag}.json"

    steps: list[dict[str, Any]] = []

    def step(name: str, cmd: list[str]) -> bool:
        rc = _run(cmd)
        steps.append({"step": name, "exit_code": rc})
        return rc == 0

    if not args.skip_yfinance:
        if not step(
            "market_psych_yfinance",
            [
                sys.executable,
                "scripts/build_market_psychology_kospi_from_yfinance_v1.py",
                "--days",
                str(args.psych_days),
            ],
        ):
            return 2

    if not step(
        "per_date_directions",
        [
            sys.executable,
            "scripts/build_btrack_per_date_directions_agct_market_psych_v1.py",
            "--market-psych-csv",
            str(psych_csv),
            "--dna-weight",
            "0",
            "--market-weight",
            "1",
            "--out",
            str(per_date),
        ],
    ):
        return 2

    step(
        "sasang_dna_market_reasoning",
        [
            sys.executable,
            "scripts/run_sasang_dna_market_reasoning_v1.py",
            "--market-psych-csv",
            str(psych_csv),
            "--output-json",
            str(reasoning_out),
        ],
    )

    btc_csv = ROOT / "research/market_data/btc_daily_external_yf.csv"
    score_cmd = [
        sys.executable,
        "scripts/build_btrack_prophecy_score_from_ohlcv.py",
        "--per-date-direction-json",
        str(per_date),
        "--recent-trading-days",
        str(args.eval_days),
        "--output",
        str(score_json),
        "--force-dual-leg-panel",
    ]
    if btc_csv.is_file():
        score_cmd.extend(["--btc-csv", str(btc_csv)])
    if not step("prophecy_score", score_cmd):
        return 2

    step(
        "eval_kospi",
        [
            sys.executable,
            "scripts/eval_prophecy_hit_rate_v1.py",
            "--run-mode",
            "price",
            "--score-json",
            str(score_json),
            "--headline-instrument",
            "kospi",
            "--output",
            str(eval_kospi),
        ],
    )
    step(
        "eval_btc",
        [
            sys.executable,
            "scripts/eval_prophecy_hit_rate_v1.py",
            "--run-mode",
            "price",
            "--score-json",
            str(score_json),
            "--headline-instrument",
            "btc",
            "--output",
            str(eval_btc),
        ],
    )

    # B-track proxy gate snapshot (non-fatal; may fail if tmp weights missing)
    daily_rc = step(
        "agct_daily_gate",
        [sys.executable, "scripts/run_agct_sasang_btrack_daily_chain_v1.py"],
    )
    agct_daily = _read_eval(ROOT / "reports/agct_sasang_btrack_daily_chain_v1_latest.json")
    holdout_session = _read_eval(ROOT / "reports/session_myeongni_hybrid_holdout_252d_v1.json")
    hybrid_30 = _read_eval(ROOT / "reports/session_myeongni_ab_hybrid_30d_v1.json")

    summary = {
        "schema": "agct_market_psych_price_eval_chain_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "research_only": True,
        "not_promoted_track_a": True,
        "window": {"eval_days": args.eval_days, "psych_days": args.psych_days},
        "operating_principle_v1": {
            "human_rail": "AGCT/DNA·cohort — not mixed into index per-date (B-track cohort chain separate)",
            "market_rail_per_date": {"dna_weight": 0.0, "market_weight": 1.0},
        },
        "price_hit_rate_eval": {
            "kospi": _hit(_read_eval(eval_kospi)),
            "btc": _hit(_read_eval(eval_btc)),
            "n_evaluated": (_read_eval(eval_kospi) or {}).get("metrics", {}).get("n_evaluated"),
            "score_json": str(score_json.relative_to(ROOT)).replace("\\", "/"),
            "per_date_json": str(per_date.relative_to(ROOT)).replace("\\", "/"),
        },
        "b_track_proxy_gate": {
            "daily_chain_ok": daily_rc,
            "external_accuracy": (agct_daily or {}).get("metrics", {}).get("external_accuracy_observed"),
            "external_risk_corr": (agct_daily or {}).get("metrics", {}).get("external_risk_corr_observed"),
            "decision": (agct_daily or {}).get("decision"),
            "note": "external_accuracy is axis vs proxy label — not price hit_rate",
        },
        "cross_reference_session_hybrid": {
            "hybrid_30d_kospi": (hybrid_30 or {})
            .get("comparison_eval_prophecy_hit_rate", {})
            .get("hybrid_session_kospi_btc_bear", {})
            .get("kospi"),
            "hybrid_252d_kospi": (holdout_session or {})
            .get("eval_prophecy_hit_rate", {})
            .get("hybrid", {})
            .get("kospi"),
        },
        "pipeline_steps": steps,
        "verdict_ko": (
            "DNA+시장심리 융합 per-date 방향으로 price eval 완료. "
            "proxy GO(36%대)와 price hit는 별 지표 — comparison JSON 참고."
        ),
    }
    text = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    args.out_summary.parent.mkdir(parents=True, exist_ok=True)
    args.out_summary.write_text(text, encoding="utf-8")
    ARTIFACT_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_SUMMARY.write_text(text, encoding="utf-8")
    print(str(args.out_summary.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
