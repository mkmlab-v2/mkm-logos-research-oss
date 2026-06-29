#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-shot B-track chain: panel → swarm JSONL CSV → join → sasang proxy → eval ([HYPO]).

Subprocesses only. No HTTP. Not a trading trigger.

**Order:**
  ``build_btrack_session_instant_myeongni_panel_v1``
  → ``build_swarm_sentiment_daily_csv_from_jsonl_v1``
  → ``join_btrack_session_panel_swarm_ohlcv_v1``
  → ``enrich_btrack_wide_sasang_proxy_v1``
  → ``eval_btrack_swarm_sasang_correlation_v1``
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSONL = ROOT / "data" / "btrack" / "swarm_sentiment_daily_hypo_v1.jsonl"
DEFAULT_KOSPI = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports" / "btrack_swarm_sasang_correlation_v1_latest.json"


def _run(cmd: list[str]) -> int:
    return int(subprocess.run(cmd, cwd=str(ROOT)).returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date-from", required=True)
    ap.add_argument("--date-to", required=True)
    ap.add_argument("--calendar-mode", choices=("all", "krx_weekdays"), default="krx_weekdays")
    ap.add_argument("--iana-tz", default="Asia/Seoul")
    ap.add_argument("--hour", type=int, default=9)
    ap.add_argument("--minute", type=int, default=0)
    ap.add_argument("--out-dir", type=Path, default=ROOT / "reports")
    ap.add_argument("--tag", type=str, default="swarm_sasang")
    ap.add_argument("--swarm-jsonl", type=Path, default=DEFAULT_JSONL)
    ap.add_argument("--ohlcv-csv", type=Path, default=None)
    ap.add_argument("--ohlcv-date-col", type=str, default="Date")
    ap.add_argument("--y-col", type=str, default="ohlcv_close")
    ap.add_argument("--min-pairs", type=int, default=3, help="Override for short smoke runs.")
    ap.add_argument("--copy-latest", action="store_true", default=True)
    ap.add_argument("--no-copy-latest", action="store_false", dest="copy_latest")
    ap.add_argument("--utf8-bom", action="store_true")
    ns = ap.parse_args()

    ns.out_dir.mkdir(parents=True, exist_ok=True)
    tag = ns.tag.strip().replace("/", "_").replace("\\", "_") or "swarm_sasang"
    panel_csv = ns.out_dir / f"btrack_session_myeongni_panel_{tag}.csv"
    swarm_csv = ns.out_dir / f"btrack_swarm_daily_{tag}.csv"
    wide_csv = ns.out_dir / f"btrack_session_panel_wide_{tag}.csv"
    enriched_csv = ns.out_dir / f"btrack_session_panel_wide_{tag}_sasang.csv"
    eval_json = ns.out_dir / f"btrack_swarm_sasang_correlation_{tag}.json"

    ohlcv = ns.ohlcv_csv
    if ohlcv is None and DEFAULT_KOSPI.is_file():
        ohlcv = DEFAULT_KOSPI

    rc = _run(
        [
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
        + (["--utf8-bom"] if ns.utf8_bom else [])
    )
    if rc != 0:
        return rc

    rc = _run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_swarm_sentiment_daily_csv_from_jsonl_v1.py"),
            "--jsonl",
            str(ns.swarm_jsonl),
            "--out-csv",
            str(swarm_csv),
        ]
        + (["--utf8-bom"] if ns.utf8_bom else [])
    )
    if rc != 0:
        return rc

    cmd_join = [
        sys.executable,
        str(ROOT / "scripts" / "join_btrack_session_panel_swarm_ohlcv_v1.py"),
        "--panel-csv",
        str(panel_csv),
        "--swarm-csv",
        str(swarm_csv),
        "--swarm-date-col",
        "date",
        "--out-csv",
        str(wide_csv),
    ]
    if ohlcv and ohlcv.is_file():
        cmd_join.extend(["--ohlcv-csv", str(ohlcv), "--ohlcv-date-col", ns.ohlcv_date_col])
    if ns.utf8_bom:
        cmd_join.append("--utf8-bom")
    rc = _run(cmd_join)
    if rc != 0:
        return rc

    rc = _run(
        [
            sys.executable,
            str(ROOT / "scripts" / "enrich_btrack_wide_sasang_proxy_v1.py"),
            "--input-csv",
            str(wide_csv),
            "--out-csv",
            str(enriched_csv),
        ]
        + (["--utf8-bom"] if ns.utf8_bom else [])
    )
    if rc != 0:
        return rc

    y_col = ns.y_col
    header_line = enriched_csv.read_text(encoding="utf-8-sig").splitlines()
    headers = header_line[0].split(",") if header_line else []
    if y_col not in headers:
        for cand in ("ohlcv_close", "ohlcv_Close", "ohlcv_close".replace("close", "Close"), "elem_fire"):
            if cand in headers:
                y_col = cand
                break
        else:
            print(f"y-col not available in enriched csv headers: {headers}", file=sys.stderr)
            return 2

    rc = _run(
        [
            sys.executable,
            str(ROOT / "scripts" / "eval_btrack_swarm_sasang_correlation_v1.py"),
            "--input-csv",
            str(enriched_csv),
            "--y-col",
            y_col,
            "--min-pairs",
            str(ns.min_pairs),
            "--out-json",
            str(eval_json),
        ]
    )
    if rc != 0:
        return rc

    if ns.copy_latest and eval_json.resolve() != DEFAULT_OUT.resolve():
        DEFAULT_OUT.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(eval_json, DEFAULT_OUT)

    print(
        f"OK panel={panel_csv} swarm={swarm_csv} wide={wide_csv} enriched={enriched_csv} eval={eval_json} latest={DEFAULT_OUT}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
