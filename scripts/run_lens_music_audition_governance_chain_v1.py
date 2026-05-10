#!/usr/bin/env python3
"""M17 governance chain for lens music audition QA.

Orchestrates M15/M16 summary generation and emits a compact latest status artifact
for daily/weekly operations surfaces.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUMMARY_OUT = ROOT / "reports" / "lens_music_audition_qa_summary_latest.json"
DEFAULT_STATUS_OUT = ROOT / "reports" / "lens_music_audition_governance_status_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--chain-glob",
        type=str,
        default="reports/_tmp_m*_chain.json",
        help="ROOT-relative glob for lens_music_gate_chain_v1 inputs.",
    )
    ap.add_argument("--warn-ratio-threshold", type=float, default=0.2)
    ap.add_argument("--summary-out", type=Path, default=DEFAULT_SUMMARY_OUT)
    ap.add_argument("--status-out", type=Path, default=DEFAULT_STATUS_OUT)
    args = ap.parse_args()

    summary_cmd = [
        sys.executable,
        str(ROOT / "scripts/build_lens_music_audition_qa_summary_v1.py"),
        "--glob",
        args.chain_glob,
        "--warn-ratio-threshold",
        str(args.warn_ratio_threshold),
        "--out",
        str(args.summary_out),
    ]
    r = subprocess.run(summary_cmd, cwd=str(ROOT), capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout)
        print(r.stderr, file=sys.stderr)
        return r.returncode

    summary = json.loads(args.summary_out.read_text(encoding="utf-8"))
    gov = dict(summary.get("governance_m16") or {})
    state = str(gov.get("state", "UNKNOWN"))
    warn_ratio = float(dict(summary.get("metrics") or {}).get("warn_ratio", 0.0))
    status = {
        "schema": "lens_music_audition_governance_status_v1",
        "generated_at_utc": _utc_now(),
        "summary_path": str(args.summary_out.resolve()),
        "state": state,
        "warn_ratio": warn_ratio,
        "warn_ratio_threshold": float(gov.get("warn_ratio_threshold", args.warn_ratio_threshold)),
        "warn_count": int(gov.get("warn_count", 0)),
        "sample_count": int(gov.get("sample_count", 0)),
        "advisory_only": True,
        "note": "M17 chain status; does not override promotion or trading decisions.",
    }
    args.status_out.parent.mkdir(parents=True, exist_ok=True)
    args.status_out.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "state": state, "status_out": str(args.status_out.resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
