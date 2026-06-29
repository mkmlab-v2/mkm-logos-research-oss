#!/usr/bin/env python3
"""Daily hero board chain: morning predict · evening score · insight [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
PY = sys.executable
KST = ZoneInfo("Asia/Seoul")
OUT = ROOT / "reports/btrack_daily_hero_board_daily_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today_kst() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


def _last_krx() -> str:
    from datetime import date

    from scripts.kospi_krx_calendar_v1 import last_krx_trading_day_on_or_before

    return last_krx_trading_day_on_or_before(datetime.now(KST).date()) or _today_kst()


def run_step(name: str, cmd: list[str], *, optional: bool = False) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=600)
    row = {
        "name": name,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "tail": (proc.stdout or proc.stderr or "")[-500:],
        "optional": optional,
    }
    if proc.returncode != 0 and optional:
        row["skipped_as_optional"] = True
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--phase", choices=["morning", "evening", "all"], default="all")
    ap.add_argument("--year-month", default=datetime.now(KST).strftime("%Y-%m"))
    ap.add_argument("--skip-fx-fetch", action="store_true")
    ap.add_argument("--skip-data-refresh", action="store_true")
    ap.add_argument("--skip-kospi-loop", action="store_true")
    ap.add_argument("--skip-llm-insight", action="store_true")
    ap.add_argument("--skip-brier-monthly", action="store_true")
    ap.add_argument("--skip-evening-briefing", action="store_true")
    ns = ap.parse_args()

    today = _today_kst()
    last_sess = _last_krx()
    rows: list[dict[str, Any]] = []

    if ns.phase in ("morning", "all"):
        if not ns.skip_kospi_loop:
            rows.append(
                run_step(
                    "kospi_june_prophecy_morning",
                    ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                     str(ROOT / "scripts/Invoke-KospiJune2026ProphecyLoop_v1.ps1"),
                     "-Phase", "Morning", "-YearMonth", ns.year_month, "-SkipPanelRebuild"],
                    optional=True,
                )
            )
        rows.append(
            run_step(
                "build_hero_board_calendar",
                [PY, "scripts/build_btrack_daily_hero_board_calendar_v1.py",
                 "--year-month", ns.year_month, "--seal-date", today],
            )
        )

    if ns.phase in ("evening", "all"):
        if not ns.skip_data_refresh:
            rows.append(
                run_step(
                    "hero_board_data_refresh",
                    [PY, "scripts/run_btrack_daily_hero_board_data_refresh_v1.py"],
                    optional=True,
                )
            )
        if not ns.skip_evening_briefing:
            rows.append(
                run_step(
                    "kospi_evening_briefing_primary",
                    [
                        PY,
                        "scripts/run_kospi_evening_briefing_chain_v1.py",
                        "--session-date",
                        last_sess,
                    ],
                )
            )
        elif not ns.skip_fx_fetch:
            rows.append(run_step("fetch_usdkrw_csv", [PY, "scripts/fetch_usdkrw_yfinance_csv_v1.py"], optional=True))
            rows.append(
                run_step(
                    "fetch_kospi_csv",
                    [PY, "scripts/fetch_kospi_yfinance_csv.py", "--merge", "--start", "1990-01-01",
                     "--end", (datetime.now(KST).date().isoformat())],
                    optional=True,
                )
            )
        if not ns.skip_kospi_loop:
            rows.append(
                run_step(
                    "kospi_june_prophecy_evening",
                    ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                     str(ROOT / "scripts/Invoke-KospiJune2026ProphecyLoop_v1.ps1"),
                     "-Phase", "Evening", "-YearMonth", ns.year_month,
                     "-SkipHeavyResearch", "-SkipGovernorObs"],
                    optional=True,
                )
            )
        rows.append(
            run_step(
                "rebuild_hero_board_calendar",
                [PY, "scripts/build_btrack_daily_hero_board_calendar_v1.py", "--year-month", ns.year_month],
                optional=True,
            )
        )
        rows.append(
            run_step(
                "eval_hero_board",
                [PY, "scripts/eval_btrack_daily_hero_board_v1.py", "--as-of-kst", last_sess],
            )
        )
        rows.append(
            run_step(
                "kospi_oos_significance",
                [PY, "scripts/build_kospi_june2026_oos_significance_v1.py", "--year-month", ns.year_month],
                optional=True,
            )
        )
        rows.append(
            run_step(
                "hero_shock_gate_shadow",
                [
                    PY,
                    "scripts/build_kospi_hero_shock_gate_shadow_v1.py",
                    "--year-month",
                    ns.year_month,
                    "--as-of-kst",
                    last_sess,
                    "--append-log",
                ],
                optional=True,
            )
        )
        rows.append(
            run_step(
                "direction_rule_shadow_panel",
                [
                    PY,
                    "scripts/build_kospi_direction_rule_shadow_panel_v1.py",
                    "--year-month",
                    ns.year_month,
                    "--as-of-kst",
                    last_sess,
                ],
                optional=True,
            )
        )
        insight_cmd = [
            PY, "scripts/run_btrack_daily_hero_board_evening_insight_v1.py",
            "--session-date", last_sess,
        ]
        if ns.skip_llm_insight:
            insight_cmd.append("--skip-llm")
        rows.append(run_step("evening_insight", insight_cmd, optional=True))
        if not ns.skip_brier_monthly:
            rows.append(
                run_step(
                    "eval_general_prophecy_brier",
                    [PY, "scripts/eval_general_prophecy_brier_score.py"],
                    optional=True,
                )
            )
        rows.append(
            run_step(
                "build_hero_board_manifest",
                [PY, "scripts/build_btrack_daily_hero_board_manifest_v1.py"],
            )
        )

    blocking = [r for r in rows if r.get("exit_code", 0) != 0 and not r.get("optional")]
    ok = not blocking
    doc = {
        "schema": "btrack_daily_hero_board_daily_chain_v1",
        "generated_at_utc": _utc(),
        "research_mode": "max_b_track",
        "send_gate": "HOLD",
        "phase": ns.phase,
        "year_month": ns.year_month,
        "as_of_kst": last_sess,
        "ok": ok,
        "steps": rows,
        "blocking_failures": [r["name"] for r in blocking],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(OUT), "steps": len(rows)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
