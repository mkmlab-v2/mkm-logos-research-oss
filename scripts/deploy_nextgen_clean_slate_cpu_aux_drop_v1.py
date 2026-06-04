#!/usr/bin/env python3
"""Copy aux_drop kit to mapped share Z:\\nextgen_cpu_aux (research_only)."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "experiments/nextgen_clean_slate_cpu_v1/aux_drop"
DEFAULT_SHARE = Path("Z:/nextgen_cpu_aux")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--share-root", type=Path, default=DEFAULT_SHARE)
    ap.add_argument(
        "--merge-only",
        action="store_true",
        help="Copy/update files without rmtree (RTT/P1 server may hold share open)",
    )
    args = ap.parse_args()

    if not SRC.is_dir():
        print("error: aux_drop missing", file=sys.stderr)
        return 1
    share_parent = args.share_root.parent
    if not share_parent.exists():
        print(f"error: share not mounted: {share_parent}", file=sys.stderr)
        return 1

    if args.merge_only and args.share_root.exists():
        for item in SRC.iterdir():
            dest = args.share_root / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
    else:
        if args.share_root.exists():
            shutil.rmtree(args.share_root)
        shutil.copytree(SRC, args.share_root)

    manifest = {
        "schema": "nextgen_clean_slate_cpu_aux_drop_manifest_v1",
        "generated_at_utc": _utc(),
        "share_path": str(args.share_root),
        "hostname_expected": "DESKTOP-AP1DC83",
        "instructions_ko": (
            "보조 PC: START_ALL_ON_AUX.cmd (RTT+P1) 또는 개별 CMD; NG40=RUN_NG40_SHARD_ON_AUX.cmd; "
            "메인: Invoke-NextGenGolden40Distributed_v1.ps1 / run_nextgen_p1_aux_distributed_chain_v1.py"
        ),
    }
    (args.share_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"deployed": str(args.share_root)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
