#!/usr/bin/env python3
"""[HYPO] One-shot: 41k ON cap sweep → promotion packet refresh."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(script: str, extra: list[str]) -> int:
    cmd = [sys.executable, str(ROOT / script), *extra]
    return subprocess.run(cmd, cwd=str(ROOT)).returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--human-approve-research", action="store_true")
    ap.add_argument("--preset", default="on_beat_search")
    args = ap.parse_args()

    if _run(
        "scripts/run_nextgen_latent_indexer_eval_ng40_cap_sweep_v1.py",
        ["--lexicon-on", "--preset", args.preset],
    ):
        return 1

    extra = []
    if args.human_approve_research:
        extra.append("--human-approve-research")
        extra.extend(
            ["--note", "41k ON cap sweep beat search 2026-06-04"]
        )
    if _run("scripts/build_btrack_nextgen_promotion_candidate_packet_v1.py", extra):
        return 1

    sweep = ROOT / (
        "experiments/nextgen_clean_slate_cpu_v1/results/"
        "ng40_latent_eval_41k_on_cap_sweep_v1_latest.json"
    )
    if sweep.is_file():
        doc = json.loads(sweep.read_text(encoding="utf-8-sig"))
        print(
            json.dumps(
                {
                    "any_beat_frozen": doc.get("any_beat_frozen"),
                    "best": doc.get("best"),
                },
                ensure_ascii=False,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
