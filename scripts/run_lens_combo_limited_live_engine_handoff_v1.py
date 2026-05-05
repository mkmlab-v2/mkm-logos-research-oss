#!/usr/bin/env python3
"""Bridge lens-combo top1 candidate into engine input payload.

Non-executing chain:
1) read lens-combo candidate artifact
2) adapt to engine input schema
3) emit HOLD/READY status payload
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_CANDIDATE = ART / "btc_top1_limited_live_candidate_from_lens_combo_latest.json"
DEFAULT_SIGNOFF = ART / "promotion_signoff_decision_latest.json"
DEFAULT_OUT = ART / "btc_limited_live_engine_input_from_lens_combo_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidate-json", type=Path, default=DEFAULT_CANDIDATE)
    ap.add_argument("--signoff-json", type=Path, default=DEFAULT_SIGNOFF)
    ap.add_argument("--symbol", type=str, default="BTCUSDT")
    ap.add_argument("--approve-submit", action="store_true")
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--live", action="store_true", help="Emit non-dry-run payload (still non-executing).")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if args.live:
        args.dry_run = False

    adapter = ROOT / "scripts" / "build_btc_limited_live_engine_input_v1.py"
    cmd = [
        sys.executable,
        str(adapter),
        "--candidate-json",
        str(args.candidate_json),
        "--signoff-json",
        str(args.signoff_json),
        "--symbol",
        str(args.symbol),
        "--out",
        str(args.out),
    ]
    if args.approve_submit:
        cmd.append("--approve-submit")
    if args.dry_run:
        cmd.append("--dry-run")
    if args.live:
        cmd.append("--live")

    res = subprocess.run(cmd, cwd=str(ROOT))
    return int(res.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
