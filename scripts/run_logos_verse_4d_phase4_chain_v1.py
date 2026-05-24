#!/usr/bin/env python3
"""Track B Phase 4 chain: null corpora build then OS metrics compare (subprocess only)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_NULL_BUILDER = ROOT / "scripts" / "build_logos_verse_4d_null_corpus_v1.py"
_COMPARE = ROOT / "scripts" / "compare_logos_verse_4d_os_metrics_v1.py"


def _run(cmd: list[str]) -> int:
    r = subprocess.run(cmd, cwd=str(ROOT))
    return int(r.returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-jsonl", type=Path, default=None)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-rows", type=int, default=0)
    ap.add_argument("--sample-size", type=int, default=500)
    ap.add_argument("--top-k", type=int, default=8)
    ap.add_argument("--full-graph", action="store_true")
    ap.add_argument("--skip-null-build", action="store_true")
    ap.add_argument("--skip-compare", action="store_true")
    ap.add_argument("--skip-vector-permutation", action="store_true")
    ap.add_argument("--skip-char-shuffle", action="store_true")
    ap.add_argument("--skip-token-shuffle", action="store_true")
    ap.add_argument("--skip-apocrypha", action="store_true")
    args = ap.parse_args()

    if not args.skip_null_build:
        cmd = [
            sys.executable,
            str(_NULL_BUILDER),
            "--seed",
            str(args.seed),
            "--max-rows",
            str(args.max_rows),
        ]
        if args.input_jsonl is not None:
            cmd.extend(["--input-jsonl", str(args.input_jsonl)])
        if args.skip_vector_permutation:
            cmd.append("--skip-vector-permutation")
        if args.skip_char_shuffle:
            cmd.append("--skip-char-shuffle")
        if args.skip_token_shuffle:
            cmd.append("--skip-token-shuffle")
        if args.skip_apocrypha:
            cmd.append("--skip-apocrypha")
        rc = _run(cmd)
        if rc != 0:
            return rc

    if not args.skip_compare:
        cmd = [
            sys.executable,
            str(_COMPARE),
            "--seed",
            str(args.seed),
            "--sample-size",
            str(args.sample_size),
            "--top-k",
            str(args.top_k),
            "--max-rows",
            str(args.max_rows),
        ]
        if args.full_graph:
            cmd.append("--full-graph")
        rc = _run(cmd)
        if rc != 0:
            return rc

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
