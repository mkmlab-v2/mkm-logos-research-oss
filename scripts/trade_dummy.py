#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dummy trade entrypoint for athena_run_v1 PoC (no real orders)."""

from __future__ import annotations

import os
import sys


def main() -> int:
    key = os.environ.get("BINANCE_API_KEY", "")
    if not key:
        print("trade_dummy: BINANCE_API_KEY not set", file=sys.stderr)
        return 1
    print(f"trade_dummy: would trade with key prefix {key[:8]}...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
