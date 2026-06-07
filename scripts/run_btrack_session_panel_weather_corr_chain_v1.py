#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-shot B-track chain: session Myeongni panel CSV → join (optional weather/OHLCV) → correlation JSON.

Subprocesses only (no import side effects). No HTTP. [HYPO] / B-track — not a trading trigger.

**Order:** ``build_btrack_session_instant_myeongni_panel_v1`` → ``join_btrack_session_panel_weather_ohlcv_v1``
→ ``correlate_btrack_joined_wide_csv_v1``.

If ``--ohlcv-csv`` is set and exists, default ``--y-col`` is ``ohlcv_close``; otherwise ``elem_fire``.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> int:
    r = subprocess.run(cmd, cwd=str(ROOT))
    return int(r.returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date-from", required=True)
    ap.add_argument("--date-to", required=True)
    ap.add_argument("--calendar-mode", choices=("all", "krx_weekdays"), default="krx_weekdays")
    ap.add_argument("--iana-tz", default="Asia/Seoul")
    ap.add_argument("--hour", type=int, default=9)
    ap.add_argument("--minute", type=int, default=0)
    ap.add_argument("--out-dir", type=Path, default=ROOT / "reports")
    ap.add_argument("--tag", type=str, default="chain", help="Filename stem fragment.")
    ap.add_argument("--weather-csv", type=Path, default=None)
    ap.add_argument("--weather-date-col", type=str, default="date")
    ap.add_argument("--ohlcv-csv", type=Path, default=None)
    ap.add_argument("--ohlcv-date-col", type=str, default="Date")
    ap.add_argument(
        "--y-col",
        type=str,
        default=None,
        help="Override auto: ohlcv_close if --ohlcv-csv exists, else elem_fire.",
    )
    ap.add_argument(
        "--x-auto-prefixes",
        type=str,
        default="elem_,wthr_,ohlcv_",
        help="Passed to correlate (default: elem_,wthr_,ohlcv_).",
    )
    ap.add_argument("--min-pairs", type=int, default=3)
    ap.add_argument("--utf8-bom", action="store_true")
    ns = ap.parse_args()

    ns.out_dir.mkdir(parents=True, exist_ok=True)
    tag = ns.tag.strip().replace("/", "_").replace("\\", "_") or "chain"
    panel_csv = ns.out_dir / f"btrack_session_myeongni_panel_{tag}.csv"
    wide_csv = ns.out_dir / f"btrack_session_panel_wide_{tag}.csv"
    corr_json = ns.out_dir / f"btrack_joined_wide_correlation_{tag}.json"

    cmd_panel = [
        sys.executable,
        str(ROOT / "scripts" / "build_btrack_session_instant_myeongni_panel_v1.py"),
        "--date-from",
        ns.date_from,
        "--date-to",
        ns.date_to,
        "--iana-tz",
        ns.iana_tz,
        "--hour",
        str(ns.hour),
        "--minute",
        str(ns.minute),
        "--calendar-mode",
        ns.calendar_mode,
        "--out-csv",
        str(panel_csv),
    ]
    if ns.utf8_bom:
        cmd_panel.append("--utf8-bom")
    rc = _run(cmd_panel)
    if rc != 0:
        return rc

    cmd_join = [
        sys.executable,
        str(ROOT / "scripts" / "join_btrack_session_panel_weather_ohlcv_v1.py"),
        "--panel-csv",
        str(panel_csv),
        "--out-csv",
        str(wide_csv),
    ]
    if ns.weather_csv and ns.weather_csv.is_file():
        cmd_join.extend(["--weather-csv", str(ns.weather_csv), "--weather-date-col", ns.weather_date_col])
    if ns.ohlcv_csv and ns.ohlcv_csv.is_file():
        cmd_join.extend(["--ohlcv-csv", str(ns.ohlcv_csv), "--ohlcv-date-col", ns.ohlcv_date_col])
    if ns.utf8_bom:
        cmd_join.append("--utf8-bom")
    rc = _run(cmd_join)
    if rc != 0:
        return rc

    y_col = ns.y_col
    if not y_col:
        if ns.ohlcv_csv and ns.ohlcv_csv.is_file():
            y_col = "ohlcv_close"
        else:
            y_col = "elem_fire"

    cmd_corr = [
        sys.executable,
        str(ROOT / "scripts" / "correlate_btrack_joined_wide_csv_v1.py"),
        "--input-csv",
        str(wide_csv),
        "--y-col",
        y_col,
        "--x-auto-prefixes",
        ns.x_auto_prefixes,
        "--min-pairs",
        str(ns.min_pairs),
        "--out-json",
        str(corr_json),
    ]
    rc = _run(cmd_corr)
    if rc != 0:
        return rc

    print(f"OK panel={panel_csv} wide={wide_csv} correlation={corr_json} y_col={y_col}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
