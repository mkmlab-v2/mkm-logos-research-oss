#!/usr/bin/env python3
"""Post commander sign-off: denylist pilot + readiness + pointer refresh ([HYPO])."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SIGNOFF = ROOT / "reports/hangul_lexicon_curated_ingest_signoff_v1_latest.json"


def _run(cmd: list[str]) -> int:
    print("+", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--commander-approve",
        action="store_true",
        help="Record signoff before chain (requires pilot both_pass).",
    )
    ap.add_argument("--skip-denylist-pilot", action="store_true")
    args = ap.parse_args()

    py = sys.executable
    if args.commander_approve:
        rc = _run([py, "scripts/record_hangul_lexicon_curated_ingest_signoff_v1.py", "--commander-approve"])
        if rc != 0:
            return rc

    if not SIGNOFF.is_file():
        print("ABORT: signoff missing — run with --commander-approve or record signoff first")
        return 1

    import json

    signoff = json.loads(SIGNOFF.read_text(encoding="utf-8"))
    if not signoff.get("approved"):
        print("ABORT: signoff not approved")
        return 1

    steps: list[tuple[str, list[str]]] = [
        ("curated_pilot_refresh", [py, "scripts/run_hangul_curated_ingest_pilot_v1.py"]),
    ]
    if not args.skip_denylist_pilot:
        steps.append(("function_word_denylist", [py, "scripts/run_lexicon_function_word_denylist_pilot_v1.py"]))
    steps.extend(
        [
            ("harness_curated", [
                py,
                "scripts/build_lexicon_hangul_tokenizer_harness_v1.py",
                "--lexicon-path",
                "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41658_hangul_curated_overlay.json",
            ]),
            ("pointer", [py, "scripts/build_master_codebook_bench_lexicon_pointer_v1.py"]),
            ("readiness", [py, "scripts/build_hangul_lexicon_ingest_pipeline_readiness_v1.py"]),
        ]
    )

    for name, cmd in steps:
        rc = _run(cmd)
        if rc != 0:
            print(f"FAIL at {name} exit={rc}")
            return rc

    print("OK: post_signoff_chain complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
