#!/usr/bin/env python3
"""Track A shadow corpus eval — lightweight manifest + summary (not full multilens eval).

Counts JSONL conversation rows and writes eval + input manifest artifacts.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace-root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument(
        "--input-jsonl",
        type=Path,
        default=None,
        help="Shadow corpus JSONL (default: data/track_a_shadow/conversations_sample_v1.jsonl)",
    )
    ap.add_argument("--max-cases", type=int, default=10_000)
    ap.add_argument(
        "--out-eval",
        type=Path,
        default=None,
        help="Eval output (default: docs/final/artifacts/track_a_shadow_corpus_eval_latest.json)",
    )
    ap.add_argument(
        "--out-manifest",
        type=Path,
        default=None,
        help="Manifest output (default: docs/final/artifacts/track_a_shadow_corpus_input_manifest_latest.json)",
    )
    args = ap.parse_args()
    root: Path = args.workspace_root.resolve()
    inp = (args.input_jsonl or root / "data/track_a_shadow/conversations_sample_v1.jsonl").resolve()
    out_eval = (args.out_eval or root / "docs/final/artifacts/track_a_shadow_corpus_eval_latest.json").resolve()
    out_man = (args.out_manifest or root / "docs/final/artifacts/track_a_shadow_corpus_input_manifest_latest.json").resolve()

    if not inp.is_file():
        print(f"error: missing input jsonl: {inp}", file=sys.stderr)
        return 2

    lines = [ln for ln in inp.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]
    n = min(len(lines), max(0, args.max_cases))
    ts = _utc()

    manifest = {
        "schema": "track_a_shadow_corpus_input_manifest_v1",
        "generated_at_utc": ts,
        "source_jsonl": str(inp).replace("\\", "/"),
        "line_count_total": len(lines),
        "cases_used": n,
    }
    eval_doc = {
        "schema": "track_a_shadow_corpus_eval_v1",
        "generated_at_utc": ts,
        "status": "GO",
        "case_count": n,
        "source_input_jsonl": str(inp).replace("\\", "/"),
        "note": (
            "Summary-only shadow pass; does not invoke full multilens evaluate_report unless "
            "a separate bench runner is wired. For G12 / production claims use P0 + human gate."
        ),
    }
    out_eval.parent.mkdir(parents=True, exist_ok=True)
    out_eval.write_text(json.dumps(eval_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_man.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out_eval}")
    print(f"Wrote {out_man}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
