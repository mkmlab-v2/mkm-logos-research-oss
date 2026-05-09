#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.9, K:0.6, M:0.7}
# Balance: 90
# Purpose: Evaluate note retrieval quality with precision/recall style metrics.
# Keywords: eval, retrieval, precision, recall, gate

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
QUERY = ROOT / "scripts" / "query_context_note_memory_index_v1.py"
DEFAULT_OUT = ROOT / "docs/final/artifacts/context_note_retrieval_eval_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sqlite", type=Path, required=True)
    ap.add_argument("--qrels-json", type=Path, required=True)
    ap.add_argument("--top-k", type=int, default=8)
    ap.add_argument(
        "--retrieval-mode",
        choices=("dense", "lexical", "hybrid"),
        default="hybrid",
    )
    ap.add_argument("--sentence-transformer-model", default=None)
    ap.add_argument("--min-precision-at-k", type=float, default=0.2)
    ap.add_argument("--min-recall-at-k", type=float, default=0.4)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.qrels_json.is_file():
        print(f"Missing qrels file: {args.qrels_json}", file=sys.stderr)
        return 2
    qrels_doc = json.loads(args.qrels_json.read_text(encoding="utf-8"))
    cases = qrels_doc.get("cases", [])
    if not isinstance(cases, list) or not cases:
        print("qrels-json must contain non-empty cases[]", file=sys.stderr)
        return 2

    rows: list[dict[str, Any]] = []
    p_sum = 0.0
    r_sum = 0.0

    for case in cases:
        query = str(case.get("query", "")).strip()
        expected_paths = case.get("expected_paths", [])
        if not query or not isinstance(expected_paths, list):
            continue
        cp_cmd = [
            sys.executable,
            str(QUERY),
            "--sqlite",
            str(args.sqlite),
            "--query",
            query,
            "--top-k",
            str(args.top_k),
            "--retrieval-mode",
            args.retrieval_mode,
        ]
        if args.sentence_transformer_model:
            cp_cmd.extend(["--sentence-transformer-model", args.sentence_transformer_model])
        cp = subprocess.run(cp_cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
        if cp.returncode != 0:
            print(cp.stderr, file=sys.stderr)
            return cp.returncode
        got = json.loads(cp.stdout).get("top_k", [])
        got_paths = [str(x.get("file_path")) for x in got if isinstance(x, dict)]
        got_unique = set(got_paths)
        expected = {str(x) for x in expected_paths}
        if not expected:
            continue
        hits = len(got_unique.intersection(expected))
        precision = hits / max(len(got_unique), 1)
        recall = hits / max(len(expected), 1)
        p_sum += precision
        r_sum += recall
        rows.append(
            {
                "query": query,
                "hits": hits,
                "precision_at_k": round(precision, 6),
                "recall_at_k": round(recall, 6),
            }
        )

    if not rows:
        print("No valid eval rows generated from qrels.", file=sys.stderr)
        return 3

    macro_p = p_sum / len(rows)
    macro_r = r_sum / len(rows)
    gate_pass = macro_p >= args.min_precision_at_k and macro_r >= args.min_recall_at_k
    out = {
        "schema": "context_note_retrieval_eval_v1",
        "version": "1.0.0",
        "ts_utc": _now(),
        "non_gating_ack": True,
        "hypothesis_tier": "B",
        "retrieval_mode": args.retrieval_mode,
        "top_k": args.top_k,
        "macro_precision_at_k": round(macro_p, 6),
        "macro_recall_at_k": round(macro_r, 6),
        "gate": {
            "min_precision_at_k": args.min_precision_at_k,
            "min_recall_at_k": args.min_recall_at_k,
            "pass": gate_pass,
        },
        "rows": rows,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if gate_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())

