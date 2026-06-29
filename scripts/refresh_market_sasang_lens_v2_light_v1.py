#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Map + lens bridge only (SSOT manifest v2 psych CSV; no yfinance)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> int:
    return int(subprocess.run(cmd, cwd=str(ROOT)).returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    psych_csv = ROOT / "data/market_sasang/market_psychology_kospi_from_yfinance_v2_latest.csv"
    if not psych_csv.is_file():
        print(f"missing {psych_csv}", file=sys.stderr)
        return 2
    if _run([sys.executable, "scripts/map_market_psych_to_sasang_axis_v2.py"]):
        return 2
    return _run([sys.executable, "scripts/run_market_sasang_lens_from_market_psych_v2_v1.py"])


if __name__ == "__main__":
    raise SystemExit(main())
