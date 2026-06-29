#!/usr/bin/env python3
"""Daily B-track max prophecy evolution chain — offline-first orchestration.

Unifies general_prophecy (expanded max pack), OHLCV hit-rate, holdout evolution,
micro-signal bundle, and watchdog. research_only · send_gate HOLD · NOT Track A.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/btrack_max_prophecy_evolution_daily_chain_v1_latest.json"
PY = sys.executable


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_step(name: str, cmd: list[str], *, optional: bool = False) -> dict[str, Any]:
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    tail = ((proc.stdout or "") + (proc.stderr or ""))[-600:]
    row: dict[str, Any] = {
        "name": name,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "tail": tail,
        "optional": optional,
    }
    if optional and proc.returncode != 0:
        row["skipped_as_optional"] = True
    return row


def _resolve_inject_mode(mode: str) -> str:
    if mode != "auto":
        return mode
    if str(os.environ.get("MKM_MAX_PROPHECY_USE_GEMINI") or "").strip().lower() in ("1", "true", "yes", "on"):
        return "hybrid"
    try:
        from scripts.news_neutralizer_llm_v1 import azure_openai_config, load_workspace_dotenv

        load_workspace_dotenv()
        if azure_openai_config():
            return "hybrid"
    except Exception:
        pass
    for k in ("GEMINI_API_KEY", "GOOGLE_AI_STUDIO_API_KEY", "GOOGLE_API_KEY"):
        if (os.environ.get(k) or "").strip():
            return "hybrid"
    return "deterministic"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--holdout-profile",
        choices=["research", "ops"],
        default="research",
        help="Holdout gate profile (research = max B-track default)",
    )
    p.add_argument("--skip-micro-signal", action="store_true")
    p.add_argument("--skip-ohlcv", action="store_true", help="Skip price OHLCV score + hit-rate")
    p.add_argument("--skip-evolution", action="store_true", help="Skip holdout candidates/ablation/health")
    p.add_argument("--skip-watchdog", action="store_true")
    p.add_argument(
        "--allow-missing-watchdog-inputs",
        action="store_true",
        default=True,
        help="Pass allow-missing flags to watchdog (default on for bootstrap)",
    )
    p.add_argument(
        "--inject-mode",
        choices=["auto", "deterministic", "hybrid", "gemini"],
        default="auto",
        help="4AI forecast inject mode (auto=hybrid if MKM_MAX_PROPHECY_USE_GEMINI or Gemini key)",
    )
    p.add_argument("--skip-adapters", action="store_true", help="Skip news/macro lens adapters")
    p.add_argument("--skip-inject", action="store_true", help="Skip 4AI forecast inject")
    p.add_argument("--fetch-market", action="store_true", help="Refresh KOSPI/BTC yfinance CSVs before OHLCV")
    ns = p.parse_args()

    inject_mode = _resolve_inject_mode(ns.inject_mode)
    rows: list[dict[str, Any]] = []

    if ns.fetch_market:
        for name, script in (
            ("fetch_kospi_yfinance_csv", "scripts/fetch_kospi_yfinance_csv.py"),
            ("fetch_btc_yfinance_csv", "scripts/fetch_btc_yfinance_csv.py"),
        ):
            rows.append(run_step(name, [PY, script], optional=True))

    if not ns.skip_adapters:
        rows.append(
            run_step(
                "build_news_macro_lens_adapters",
                [PY, "scripts/build_btrack_news_macro_lens_adapters_v1.py"],
                optional=True,
            )
        )

    rows.append(
        run_step(
            "generate_general_prophecy",
            [
                PY,
                "scripts/generate_general_prophecy_v1.py",
                "--output",
                "docs/final/artifacts/general_prophecy_latest.json",
                "--stub-forecasts",
            ],
        )
    )

    if not ns.skip_inject:
        rows.append(
            run_step(
                "inject_mkm_4ai_forecasts_max_evolution",
                [
                    PY,
                    "scripts/inject_mkm_4ai_forecasts_max_evolution_v1.py",
                    "--mode",
                    inject_mode,
                    "--question-id-prefix",
                    "max.",
                ],
                optional=True,
            )
        )

    rows.append(
        run_step(
            "build_general_prophecy_brief",
            [
                PY,
                "scripts/build_general_prophecy_brief.py",
                "--input",
                "docs/final/artifacts/general_prophecy_latest.json",
                "--output",
                "docs/final/artifacts/general_prophecy_brief_latest.md",
            ],
        )
    )

    rows.append(
        run_step(
            "eval_general_prophecy_brier",
            [
                PY,
                "scripts/eval_general_prophecy_brier_score.py",
                "--input",
                "docs/final/artifacts/general_prophecy_latest.json",
                "--output",
                "docs/final/artifacts/general_prophecy_brier_eval_latest.json",
            ],
        )
    )

    rows.append(
        run_step(
            "build_general_prophecy_explainable",
            [
                PY,
                "scripts/build_general_prophecy_explainable_v1.py",
                "--input",
                "docs/final/artifacts/general_prophecy_latest.json",
                "--output",
                "docs/final/artifacts/general_prophecy_explainable_latest.json",
            ],
        )
    )

    rows.append(
        run_step(
            "holdout_gate",
            [
                PY,
                "scripts/check_general_prophecy_explainability_holdout_gate_v1.py",
                "--profile",
                ns.holdout_profile,
                "--output-json",
                "docs/final/artifacts/general_prophecy_explainability_holdout_gate_v1_latest.json",
            ],
            optional=True,
        )
    )

    if not ns.skip_micro_signal:
        rows.append(
            run_step(
                "build_micro_signal_bundle",
                [PY, "scripts/build_micro_signal_observation_bundle_v1.py"],
                optional=True,
            )
        )
        rows.append(
            run_step(
                "validate_micro_signal_bundle",
                [PY, "scripts/validate_micro_signal_observation_bundle_v1.py"],
                optional=True,
            )
        )

    if not ns.skip_ohlcv:
        kospi_csv = ROOT / "research/market_data/kospi_daily_external_yf.csv"
        if kospi_csv.is_file():
            rows.append(
                run_step(
                    "build_btrack_prophecy_score_ohlcv",
                    [
                        PY,
                        "scripts/build_btrack_prophecy_score_from_ohlcv.py",
                        "--eval-date",
                        "auto",
                    ],
                    optional=True,
                )
            )
            rows.append(
                run_step(
                    "eval_prophecy_hit_rate",
                    [
                        PY,
                        "scripts/eval_prophecy_hit_rate_v1.py",
                        "--run-mode",
                        "price",
                        "--score-json",
                        "docs/final/artifacts/btrack_prophecy_score_latest.json",
                        "--output",
                        "docs/final/artifacts/prophecy_hit_rate_eval_latest.json",
                    ],
                    optional=True,
                )
            )
        else:
            rows.append(
                {
                    "name": "build_btrack_prophecy_score_ohlcv",
                    "skipped": True,
                    "reason": "missing_kospi_csv",
                    "optional": True,
                }
            )

    if not ns.skip_evolution:
        rows.append(
            run_step(
                "holdout_evolution_candidates",
                [PY, "scripts/build_general_prophecy_holdout_evolution_candidates_v1.py"],
                optional=True,
            )
        )
        rows.append(
            run_step(
                "holdout_evolution_ablation",
                [PY, "scripts/run_general_prophecy_holdout_evolution_ablation_v1.py"],
                optional=True,
            )
        )
        rows.append(
            run_step(
                "evolution_health",
                [PY, "scripts/build_general_prophecy_evolution_health_v1.py"],
                optional=True,
            )
        )

    if not ns.skip_watchdog:
        wd_cmd = [PY, "scripts/check_prophecy_evolution_watchdog_v1.py"]
        if ns.allow_missing_watchdog_inputs:
            wd_cmd.extend(["--allow-missing-ablation", "--allow-missing-hit-rate"])
        rows.append(run_step("prophecy_evolution_watchdog", wd_cmd, optional=True))

    rows.append(
        run_step(
            "build_max_evolution_manifest",
            [PY, "scripts/build_btrack_max_prophecy_evolution_manifest_v1.py"],
        )
    )

    blocking_fail = [
        r
        for r in rows
        if r.get("exit_code", 0) != 0
        and not r.get("optional")
        and not r.get("skipped")
    ]
    ok = len(blocking_fail) == 0

    doc = {
        "schema": "btrack_max_prophecy_evolution_daily_chain_v1",
        "generated_at_utc": _utc(),
        "research_mode": "max_b_track",
        "send_gate": "HOLD",
        "boundary_ack": True,
        "holdout_profile": ns.holdout_profile,
        "inject_mode": inject_mode,
        "ok": ok,
        "steps": rows,
        "blocking_failures": [r["name"] for r in blocking_fail],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(OUT), "steps": len(rows)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
