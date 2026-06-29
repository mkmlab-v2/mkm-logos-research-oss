#!/usr/bin/env python3
"""Evening data refresh for daily hero board: flow · FX · weather · pre-news [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PY = sys.executable
KST = ZoneInfo("Asia/Seoul")
OUT = ROOT / "reports/btrack_daily_hero_board_data_refresh_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _month_bounds() -> tuple[str, str, str]:
    today = datetime.now(KST).date()
    d0 = today.replace(day=1)
    if today.month == 12:
        d1 = today.replace(day=31)
    else:
        d1 = (today.replace(month=today.month + 1, day=1) - timedelta(days=1))
    arch = today - timedelta(days=1)
    return d0.isoformat(), d1.isoformat(), arch.isoformat()


def run_step(name: str, cmd: list[str], *, optional: bool = False) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=300)
    row = {
        "name": name,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "tail": (proc.stdout or proc.stderr or "")[-400:],
        "optional": optional,
    }
    if proc.returncode != 0 and optional:
        row["skipped_as_optional"] = True
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-flow", action="store_true")
    ap.add_argument("--skip-weather", action="store_true")
    ap.add_argument("--skip-pre-news", action="store_true")
    ap.add_argument("--skip-news-macro", action="store_true")
    ns = ap.parse_args()

    today = datetime.now(KST).date()
    flow_from = (today - timedelta(days=7)).isoformat()
    flow_to = today.isoformat()
    m_from, m_to, arch_through = _month_bounds()

    rows: list[dict[str, Any]] = []

    rows.append(run_step("fetch_kospi_csv", [PY, "scripts/fetch_kospi_yfinance_csv.py", "--merge", "--start", "1990-01-01", "--end", (today + timedelta(days=1)).isoformat()], optional=True))
    rows.append(run_step("fetch_usdkrw_csv", [PY, "scripts/fetch_usdkrw_yfinance_csv_v1.py"], optional=True))

    if not ns.skip_flow:
        rows.append(
            run_step(
                "fetch_kospi_flow_pykrx",
                [PY, "scripts/fetch_kospi_daily_flow_pykrx_v1.py", "--from-date", flow_from, "--to-date", flow_to],
                optional=True,
            )
        )
        rows.append(run_step("rollup_monthly_flow", [PY, "scripts/rollup_kospi_monthly_flow_from_daily_v1.py"], optional=True))

    if not ns.skip_weather:
        rows.append(
            run_step(
                "build_korea_weather_openmeteo",
                [
                    PY,
                    "scripts/build_korea_daily_weather_openmeteo_v1.py",
                    "--date-from",
                    m_from,
                    "--date-to",
                    m_to,
                    "--archive-through",
                    arch_through,
                ],
                optional=True,
            )
        )
        rows.append(
            run_step(
                "sync_hero_board_weather_gt",
                [PY, "scripts/sync_hero_board_weather_gt_from_openmeteo_v1.py"],
                optional=True,
            )
        )

    if not ns.skip_pre_news:
        rows.append(
            run_step(
                "fetch_naver_pre_news",
                [
                    PY,
                    "scripts/fetch_naver_openapi_signals_v1.py",
                    "--news-query",
                    "코스피 환율 CPI FOMC",
                    "--allow-cache-fallback",
                ],
                optional=True,
            )
        )
        rows.append(
            run_step(
                "archive_pre_news_daily",
                [PY, "scripts/archive_pre_news_shadow_daily_v1.py"],
                optional=True,
            )
        )

    if not ns.skip_news_macro:
        adapter = ROOT / "scripts/build_btrack_news_macro_lens_adapters_v1.py"
        if adapter.is_file():
            rows.append(run_step("build_news_macro_adapters", [PY, str(adapter)], optional=True))
            rows.append(
                run_step(
                    "build_macro_news_headline_verify",
                    [PY, "scripts/build_btrack_macro_news_shock_headline_verify_v1.py"],
                    optional=True,
                )
            )

    # Session JSONL through end of next month for per-date lens CF
    if today.month == 12:
        jsonl_through = today.replace(year=today.year + 1, month=1, day=31)
    else:
        jsonl_through = (today.replace(month=today.month + 2, day=1) - timedelta(days=1))
    rows.append(
        run_step(
            "extend_manseryeok_session_jsonl",
            [
                PY,
                "scripts/extend_manseryeok_session_jsonl_v1.py",
                "--through-date",
                jsonl_through.isoformat(),
            ],
            optional=True,
        )
    )

    blocking = [r for r in rows if r.get("exit_code", 0) != 0 and not r.get("optional")]
    ok = not blocking
    doc = {
        "schema": "btrack_daily_hero_board_data_refresh_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
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
