#!/usr/bin/env python3
"""Track B: gap staging → union JSONL → verse 4D phases 1–4 (full) → showroom/B2B."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

UNION_JSONL = ROOT / "data/logos/verse_decoded_v2_union_v1.jsonl"


def _run(cmd: list[str]) -> int:
    print(" ".join(cmd), flush=True)
    return int(subprocess.run(cmd, cwd=str(ROOT)).returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-staging", action="store_true")
    ap.add_argument("--skip-union", action="store_true")
    ap.add_argument("--skip-coverage-diff", action="store_true")
    ap.add_argument("--skip-phase1", action="store_true")
    ap.add_argument("--skip-phase2", action="store_true")
    ap.add_argument("--skip-phase3", action="store_true")
    ap.add_argument("--skip-phase4", action="store_true")
    ap.add_argument("--skip-showroom", action="store_true")
    ap.add_argument("--sample-size", type=int, default=31102)
    args = ap.parse_args()

    py = sys.executable
    steps: list[tuple[str, list[str]]] = []

    if not args.skip_staging:
        steps.append(("gap_staging", [py, str(ROOT / "scripts/build_logos_verse_gap_staging_v1.py")]))
    if not args.skip_union:
        steps.append(("union_merge", [py, str(ROOT / "scripts/merge_logos_verse_decoded_union_v1.py")]))
    if not args.skip_coverage_diff:
        steps.append(("coverage_diff", [py, str(ROOT / "scripts/build_logos_verse_canon_coverage_diff_v1.py")]))
    if not args.skip_phase1:
        steps.append(
            (
                "phase1_corpus_union",
                [
                    py,
                    str(ROOT / "scripts/build_logos_verse_4d_corpus_v1.py"),
                    "--input-jsonl",
                    str(UNION_JSONL),
                ],
            )
        )
    if not args.skip_phase2:
        steps.append(("phase2_graph", [py, str(ROOT / "scripts/build_logos_verse_4d_graph_v1.py")]))
    if not args.skip_phase3:
        steps.append(("phase3_lexicon", [py, str(ROOT / "scripts/project_logos_verse_4d_to_lexicon_v1.py")]))
    if not args.skip_phase4:
        steps.append(
            (
                "phase4_full_graph",
                [
                    py,
                    str(ROOT / "scripts/run_logos_verse_4d_phase4_chain_v1.py"),
                    "--full-graph",
                    "--sample-size",
                    str(args.sample_size),
                    "--max-rows",
                    "0",
                ],
            )
        )
    if not args.skip_showroom:
        steps.append(
            ("showroom_b2b", [py, str(ROOT / "scripts/run_logos_verse_4d_showroom_b2b_chain_v1.py")])
        )

    for name, cmd in steps:
        print(f"[gap-union-rebuild] {name}", flush=True)
        rc = _run(cmd)
        if rc != 0:
            print(f"[gap-union-rebuild] failed {name} exit={rc}", flush=True)
            return rc
    print("[gap-union-rebuild] done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
