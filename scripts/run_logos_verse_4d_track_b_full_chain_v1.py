#!/usr/bin/env python3
"""Track B one-shot: logos verse 4D phases 1–4 (corpus → graph → lexicon → null compare)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_STEPS = (
    ("phase1_corpus", [sys.executable, str(ROOT / "scripts/build_logos_verse_4d_corpus_v1.py")]),
    ("phase2_graph", [sys.executable, str(ROOT / "scripts/build_logos_verse_4d_graph_v1.py")]),
    ("phase3_lexicon", [sys.executable, str(ROOT / "scripts/project_logos_verse_4d_to_lexicon_v1.py")]),
    (
        "phase4_null_compare",
        [sys.executable, str(ROOT / "scripts/run_logos_verse_4d_phase4_chain_v1.py")],
    ),
)


def _run(cmd: list[str]) -> int:
    print(" ".join(cmd), flush=True)
    return int(subprocess.run(cmd, cwd=str(ROOT)).returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-rows", type=int, default=0, help="0 = full corpus (passed to sub-steps)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--skip-phase1", action="store_true")
    ap.add_argument("--skip-phase2", action="store_true")
    ap.add_argument("--skip-phase3", action="store_true")
    ap.add_argument("--skip-phase4", action="store_true")
    ap.add_argument("--recompute-audit", action="store_true", help="Phase1 gematria recompute")
    args = ap.parse_args()

    for name, base_cmd in _STEPS:
        if name == "phase1_corpus" and args.skip_phase1:
            continue
        if name == "phase2_graph" and args.skip_phase2:
            continue
        if name == "phase3_lexicon" and args.skip_phase3:
            continue
        if name == "phase4_null_compare" and args.skip_phase4:
            continue

        cmd = list(base_cmd)
        if name in ("phase1_corpus", "phase3_lexicon", "phase4_null_compare"):
            if args.max_rows:
                cmd.extend(["--max-rows", str(args.max_rows)])
        if name == "phase4_null_compare":
            cmd.extend(["--seed", str(args.seed)])
        if name == "phase1_corpus" and args.recompute_audit:
            cmd.append("--recompute-audit")

        print(f"[track-b-full] {name}", flush=True)
        rc = _run(cmd)
        if rc != 0:
            print(f"[track-b-full] failed {name} exit={rc}", flush=True)
            return rc

    print("[track-b-full] done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
