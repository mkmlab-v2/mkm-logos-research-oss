#!/usr/bin/env python3
"""Build + append Logos query path ledger from router sidecar (repro entrypoint)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.logos_query_path_ledger_v1 import main  # noqa: E402

if __name__ == "__main__":
    argv = ["from-router", *sys.argv[1:]]
    raise SystemExit(main(argv))
