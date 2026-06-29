#!/usr/bin/env python3
"""Session end chain: resolve deep fetch → turn_meta append → CENTRAL checkpoint."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESOLVE = ROOT / "scripts/resolve_deep_fetch_from_handoff_v1.py"
APPEND = ROOT / "scripts/append_mkm_cursor_turn_meta_v1.py"
CHECKPOINT = ROOT / "scripts/athena_checkpoint.py"


def _run(cmd: list[str], *, label: str) -> int:
    proc = subprocess.run(cmd, cwd=ROOT, check=False)
    if proc.returncode != 0:
        print(f"FAIL: {label} exit {proc.returncode}", file=sys.stderr)
    return int(proc.returncode)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lane", default="infra")
    parser.add_argument("--continuity-id", required=True)
    parser.add_argument("message", nargs="?", default="")
    parser.add_argument("--message", dest="message_flag", default="", help="Alias for message arg")
    parser.add_argument("--skip-resolve", action="store_true")
    parser.add_argument("--skip-append", action="store_true")
    parser.add_argument("--skip-checkpoint", action="store_true")
    parser.add_argument("--no-patch-envelope", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    msg = (args.message or args.message_flag or "").strip()
    if not msg:
        print("error: message required", file=sys.stderr)
        return 1

    continuity_id = args.continuity_id.strip()
    lane = args.lane.strip() or "infra"

    if args.dry_run:
        print(
            f"DRY: resolve lane={lane} patch={not args.no_patch_envelope} "
            f"append continuity={continuity_id} checkpoint msg={msg!r}"
        )
        return 0

    if not args.skip_resolve:
        resolve_cmd = [
            sys.executable,
            str(RESOLVE),
            "--lane",
            lane,
        ]
        if not args.no_patch_envelope:
            resolve_cmd.append("--patch-envelope")
        code = _run(resolve_cmd, label="resolve_deep_fetch")
        if code != 0:
            return code

    if not args.skip_append:
        code = _run(
            [
                sys.executable,
                str(APPEND),
                "--lane",
                lane,
                "--continuity-id",
                continuity_id,
                "--checkpoint-message",
                msg,
            ],
            label="append_turn_meta",
        )
        if code != 0:
            return code

    if not args.skip_checkpoint:
        code = _run(
            [
                sys.executable,
                str(CHECKPOINT),
                "--continuity-id",
                continuity_id,
                "--lane",
                lane,
                "--skip-turn-meta",
                msg,
            ],
            label="athena_checkpoint",
        )
        if code != 0:
            return code

    print(f"OK: session_end lane={lane} continuity_id={continuity_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
