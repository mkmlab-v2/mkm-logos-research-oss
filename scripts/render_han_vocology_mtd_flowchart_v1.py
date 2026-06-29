# -*- coding: utf-8 -*-
"""Backward-compatible wrapper — use render_han_vocology_flowchart_v1.py --spec ..."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.render_han_vocology_flowchart_v1 import main as _main  # noqa: E402

DEFAULT_SPEC = ROOT / "docs/final/artifacts/han_vocology_mtd_flowchart_spec_v1.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/han_vocology_fig07_01_mtd_protocol_flow_v1_latest.png"
DEFAULT_REPORT = ROOT / "reports/han_vocology_mtd_flowchart_render_v1_latest.json"


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Render MTD flowchart (wrapper)")
    ap.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    args = ap.parse_args()
    sys.argv = [
        "render_han_vocology_flowchart_v1.py",
        "--spec",
        str(args.spec),
        "--out",
        str(args.out),
        "--report-out",
        str(args.report_out),
    ]
    raise SystemExit(_main())
