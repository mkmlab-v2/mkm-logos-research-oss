#!/usr/bin/env python3
"""Track A v3 merge apply chain — commander signoff + production lexicon swap."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(cmd: list[str]) -> int:
    print("+", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--commander-track-a-merge-approve",
        action="store_true",
        help="Record signoff and apply production swap (requires preflight_ready).",
    )
    ap.add_argument("--dry-run-apply", action="store_true")
    ap.add_argument("--note", default="", help="Commander note on signoff.")
    args = ap.parse_args()

    if not args.commander_track_a_merge_approve:
        print("ABORT: pass --commander-track-a-merge-approve")
        return 1

    py = sys.executable
    signoff_cmd = [
        py,
        "scripts/record_hangul_v3_track_a_merge_commander_signoff_v1.py",
        "--commander-track-a-merge-approve",
    ]
    if args.note.strip():
        signoff_cmd.extend(["--note", args.note.strip()])
    rc = _run(signoff_cmd)
    if rc != 0:
        return rc

    apply_cmd = [py, "scripts/apply_hangul_v3_track_a_merge_production_lexicon_v1.py"]
    if args.dry_run_apply:
        apply_cmd.append("--dry-run")
    rc = _run(apply_cmd)
    if rc != 0:
        return rc

    report = {
        "schema": "hangul_v3_track_a_merge_apply_chain_v1",
        "ok": True,
        "dry_run_apply": args.dry_run_apply,
        "signoff": "docs/final/artifacts/hangul_v3_track_a_merge_commander_signoff_v1_latest.json",
        "apply_log": "reports/hangul_v3_track_a_merge_production_lexicon_apply_v1_latest.json",
    }
    out = ROOT / "reports/hangul_v3_track_a_merge_apply_chain_v1_latest.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"OK": "hangul_v3_track_a_merge_apply_chain complete"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
