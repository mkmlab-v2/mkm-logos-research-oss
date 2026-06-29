#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minimal daily KOSPI observation loop (5 steps) [HYPO][research_only].

Morning: optional calendar seal. Evening: score · feedback · shadow · significance.
Does NOT apply weights or promote Track A.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/kospi_daily_observation_loop_v1_latest.json"
PY = sys.executable


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _as_of() -> str:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.kospi_krx_calendar_v1 import last_krx_trading_day_on_or_before

    return last_krx_trading_day_on_or_before(date.today()) or date.today().isoformat()


def _run(name: str, cmd: list[str], *, optional: bool = False) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {
        "name": name,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "optional": optional,
        "tail": ((proc.stdout or "") + (proc.stderr or ""))[-400:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year-month", default=None)
    ap.add_argument("--as-of-kst", default=None)
    ap.add_argument("--phase", choices=("evening", "morning", "all"), default="evening")
    ap.add_argument("--skip-fetch", action="store_true")
    ap.add_argument("--skip-miss-insight", action="store_true")
    ap.add_argument("--output", type=Path, default=OUT)
    ns = ap.parse_args()
    as_of = ns.as_of_kst or _as_of()
    ym = ns.year_month or as_of[:7]
    tag = ym.replace("-", "")
    cal = ROOT / f"reports/kospi_{tag}_daily_prophecy_calendar_v1.json"
    if ym == "2026-06" and not cal.is_file():
        cal = ROOT / "reports/kospi_june2026_daily_prophecy_calendar_v1.json"
    steps: list[dict[str, Any]] = []

    if ns.phase in ("morning", "all"):
        steps.append(
            _run(
                "1_morning_calendar",
                [PY, "scripts/build_kospi_june2026_daily_prophecy_calendar_v1.py", "--year-month", ym, "--skip-panel-rebuild", "--profile", "v2_multilens", "--seal-date", date.today().isoformat()],
            )
        )

    if ns.phase in ("evening", "all"):
        if not ns.skip_fetch:
            fetch = ROOT / "scripts/fetch_kospi_yfinance_csv.py"
            if fetch.is_file():
                steps.append(
                    _run(
                        "1_fetch_ohlcv",
                        [PY, str(fetch), "--merge", "--start", "1990-01-01", "--end", date.today().isoformat(), "--fill-recent-gaps"],
                        optional=True,
                    )
                )
        steps.append(
            _run(
                "2_eval_scoring_shadow",
                [PY, "scripts/eval_kospi_june2026_daily_prophecy_v1.py", "--calendar-json", str(cal), "--as-of-kst", as_of],
            )
        )
        steps.append(
            _run(
                "3_channel_feedback_log",
                [PY, "scripts/build_kospi_daily_channel_feedback_log_v1.py", "--year-month", ym, "--as-of-kst", as_of],
            )
        )
        steps.append(
            _run(
                "4_parallel_shadow_bundle",
                [PY, "scripts/build_kospi_june2026_parallel_shadow_bundle_v1.py", "--year-month", ym, "--as-of-kst", as_of, "--calendar-json", str(cal)],
            )
        )
        drill_csv = ROOT / f"reports/kospi_{tag}_composite_shadow_daily_drill_v1.csv"
        steps.append(
            _run(
                "4b_drill_csv",
                [PY, "scripts/export_kospi_composite_shadow_daily_drill_v1.py", "--year-month", ym, "--output-csv", str(drill_csv)],
                optional=True,
            )
        )
        steps.append(
            _run(
                "5_oos_significance",
                [PY, "scripts/build_kospi_june2026_oos_significance_v1.py", "--year-month", ym],
            )
        )
        if ym >= "2026-07":
            steps.append(
                _run(
                    "5b_july_readiness",
                    [PY, "scripts/build_kospi_july_forward_oos_readiness_v1.py", "--as-of-kst", as_of],
                    optional=True,
                )
            )
        if not ns.skip_miss_insight:
            miss = [
                PY,
                "scripts/run_kospi_june2026_evening_miss_insight_chain_v1.py",
                "--as-of-kst",
                as_of,
                "--calendar-json",
                str(cal),
                "--skip-llm",
            ]
            steps.append(_run("optional_miss_insight", miss, optional=True))
        steps.append(
            _run(
                "optional_per_date_lens_shadow_chain",
                [
                    PY,
                    "scripts/run_kospi_per_date_lens_shadow_chain_v1.py",
                    "--year-month",
                    ym,
                    "--as-of-kst",
                    as_of,
                    "--skip-jsonl-extend",
                    "--skip-panel-rebuild",
                ],
                optional=True,
            )
        )
        steps.append(
            _run(
                "optional_sasang_veto_shadow",
                [
                    PY,
                    "scripts/build_kospi_sasang_veto_blend_shadow_v1.py",
                    "--year-month",
                    ym,
                    "--as-of-kst",
                    as_of,
                ],
                optional=True,
            )
        )
        steps.append(
            _run(
                "optional_oos_dual_hr_report",
                [
                    PY,
                    "scripts/build_kospi_oos_dual_hr_report_v1.py",
                    "--year-month",
                    ym,
                    "--as-of-kst",
                    as_of,
                ],
                optional=True,
            )
        )
        steps.append(
            _run(
                "optional_per_date_weight_counterfactual",
                [
                    PY,
                    "scripts/build_kospi_per_date_weight_counterfactual_shadow_v1.py",
                    "--year-month",
                    ym,
                    "--as-of-kst",
                    as_of,
                ],
                optional=True,
            )
        )
        steps.append(
            _run(
                "optional_dual_path_conflict_shadow",
                [
                    PY,
                    "scripts/build_kospi_dual_path_conflict_shadow_v1.py",
                    "--year-month",
                    ym,
                    "--as-of-kst",
                    as_of,
                ],
                optional=True,
            )
        )

    required_fail = [s for s in steps if not s.get("optional") and s["exit_code"] != 0]
    feedback = {}
    fp = ROOT / "reports/kospi_daily_channel_feedback_latest.json"
    if fp.is_file():
        feedback = json.loads(fp.read_text(encoding="utf-8-sig"))
    doc = {
        "schema": "kospi_daily_observation_loop_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "auto_apply": False,
        "phase": ns.phase,
        "year_month": ym,
        "as_of_kst": as_of,
        "quality_ok": len(required_fail) == 0,
        "steps": steps,
        "feedback_log": feedback,
        "five_step_ko": [
            "1 OHLCV fetch (optional) + eval 채점",
            "2 channel feedback jsonl (FAIL rescue 플래그)",
            "3 parallel shadow bundle + drill CSV",
            "4 Wilson/significance",
            "5 July readiness (해당 월)",
        ],
        "reproduce": f"py scripts/run_kospi_daily_observation_loop_v1.py --year-month {ym} --phase evening",
    }
    ns.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    art = ROOT / "docs/final/artifacts/kospi_daily_observation_loop_v1_latest.json"
    art.parent.mkdir(parents=True, exist_ok=True)
    art.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["quality_ok"], "as_of": as_of, "year_month": ym}, ensure_ascii=False))
    return 1 if required_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
