#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.8, L:0.9, K:0.7, M:0.8}
# Balance: 91
# Purpose: One-shot chain for research profile build and retrieval gate evaluation.
# Keywords: chain, retrieval, eval, gate, sqlite

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BUILD_PROFILES = ROOT / "scripts" / "build_context_note_memory_profiles_v1.py"
EVAL = ROOT / "scripts" / "eval_context_note_retrieval_v1.py"

DEFAULT_QRELS = ROOT / "tests/fixtures/context_note_qrels_sample_v1.json"
DEFAULT_SQLITE = ROOT / "docs/final/artifacts/context_note_memory_research_v1.sqlite"
DEFAULT_EVAL_OUT = ROOT / "docs/final/artifacts/context_note_retrieval_eval_research_latest.json"
DEFAULT_SUMMARY = ROOT / "docs/final/artifacts/context_note_research_gate_summary_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> tuple[int, str, str]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    return cp.returncode, cp.stdout.strip(), cp.stderr.strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sentence-transformer-model", default="all-MiniLM-L6-v2")
    ap.add_argument("--qrels-json", type=Path, default=DEFAULT_QRELS)
    ap.add_argument("--sqlite", type=Path, default=DEFAULT_SQLITE)
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--min-precision-at-k", type=float, default=0.2)
    ap.add_argument("--min-recall-at-k", type=float, default=0.7)
    ap.add_argument("--eval-out", type=Path, default=DEFAULT_EVAL_OUT)
    ap.add_argument("--summary-out", type=Path, default=DEFAULT_SUMMARY)
    args = ap.parse_args()

    build_cmd = [
        sys.executable,
        str(BUILD_PROFILES),
        "--sentence-transformer-model",
        args.sentence_transformer_model,
    ]
    b_code, b_out, b_err = _run(build_cmd)

    eval_cmd = [
        sys.executable,
        str(EVAL),
        "--sqlite",
        str(args.sqlite),
        "--qrels-json",
        str(args.qrels_json),
        "--retrieval-mode",
        "hybrid",
        "--top-k",
        str(args.top_k),
        "--sentence-transformer-model",
        args.sentence_transformer_model,
        "--min-precision-at-k",
        str(args.min_precision_at_k),
        "--min-recall-at-k",
        str(args.min_recall_at_k),
        "--out-json",
        str(args.eval_out),
    ]
    e_code, e_out, e_err = _run(eval_cmd)

    gate_doc: dict[str, Any] = {}
    if args.eval_out.is_file():
        gate_doc = json.loads(args.eval_out.read_text(encoding="utf-8"))

    overall_ok = b_code == 0 and e_code == 0
    summary = {
        "schema": "context_note_research_gate_summary_v1",
        "version": "1.0.0",
        "ts_utc": _now(),
        "overall_ok": overall_ok,
        "steps": {
            "build_profiles": {
                "exit_code": b_code,
                "ok": b_code == 0,
                "stdout": b_out,
                "stderr": b_err,
            },
            "eval_gate": {
                "exit_code": e_code,
                "ok": e_code == 0,
                "stdout": e_out,
                "stderr": e_err,
                "metrics": {
                    "macro_precision_at_k": gate_doc.get("macro_precision_at_k"),
                    "macro_recall_at_k": gate_doc.get("macro_recall_at_k"),
                    "gate_pass": (gate_doc.get("gate") or {}).get("pass"),
                },
            },
        },
    }
    args.summary_out.parent.mkdir(parents=True, exist_ok=True)
    args.summary_out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

