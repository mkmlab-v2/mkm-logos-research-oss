#!/usr/bin/env python3
"""Parallel: real-corpus smoke + wave2 lemma candidates (MS HOLD)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_SUMMARY = ROOT / "reports/hangul_curated_parallel_ops_v1_latest.json"


def _run(label: str, cmd: list[str]) -> dict:
    print("+", " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "label": label,
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-2000:],
        "stderr_tail": (proc.stderr or "")[-1000:] if proc.returncode != 0 else "",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sequential", action="store_true", help="Run jobs one after another.")
    args = ap.parse_args()

    py = sys.executable
    jobs = [
        ("real_corpus_smoke", [py, "scripts/run_hangul_curated_real_corpus_smoke_v1.py"]),
        ("wave2_candidates", [py, "scripts/build_hangul_lexicon_wave2_lemma_candidates_v1.py"]),
    ]

    results: list[dict] = []
    if args.sequential:
        for label, cmd in jobs:
            results.append(_run(label, cmd))
    else:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futs = {pool.submit(_run, label, cmd): label for label, cmd in jobs}
            for fut in as_completed(futs):
                results.append(fut.result())

    summary = {
        "schema": "hangul_curated_parallel_ops_v1",
        "results": results,
        "all_ok": all(r["exit_code"] == 0 for r in results),
        "artifacts": {
            "real_corpus_smoke": "reports/hangul_curated_real_corpus_smoke_v1_latest.json",
            "wave2_candidates": "docs/final/artifacts/hangul_lexicon_wave2_lemma_candidates_v1.json",
        },
        "ms_paste_headline": "HOLD",
    }
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
