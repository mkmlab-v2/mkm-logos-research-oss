#!/usr/bin/env python3
"""Track B deep fusion job v1 — skeleton only.

Requires logos_track_b_policy_readiness_v1 overall_ok unless --skip-readiness-check.
Does not call LLM/embeddings; records inputs and execution status for offline audits.
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_READINESS = ROOT / "docs/final/artifacts/logos_track_b_policy_readiness_v1_latest.json"
DEFAULT_THEOLOGY = ROOT / "docs/final/artifacts/LOGOS_MKM_THEOLOGY_BASELINE_V1.json"
DEFAULT_BUNDLE = ROOT / "docs/final/artifacts/logos_corpus_graph_bundle_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_track_b_deep_fusion_job_v1_latest.json"

ARTIFACT_SCHEMA = "logos_track_b_deep_fusion_job_v1"
VERSION = "1.0.0"


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p.resolve())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--readiness", type=Path, default=DEFAULT_READINESS)
    ap.add_argument("--theology-baseline", type=Path, default=DEFAULT_THEOLOGY)
    ap.add_argument("--bundle-json", type=Path, default=DEFAULT_BUNDLE)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--skip-readiness-check",
        action="store_true",
        help="Do not require overall_ok (local/dev only).",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print plan summary only; still writes output when combined with default behavior.",
    )
    ap.add_argument(
        "--allow-llm-placeholder",
        action="store_true",
        help="Reserved: future hook for explicit LLM enablement (currently ignored; never calls LLM).",
    )
    args = ap.parse_args()

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    job_id = f"job_{uuid.uuid4().hex[:16]}"

    readiness_doc: dict[str, Any] = {}
    overall_ok = False
    if args.readiness.is_file():
        readiness_doc = json.loads(args.readiness.read_text(encoding="utf-8"))
        overall_ok = readiness_doc.get("overall_ok") is True
    elif not args.skip_readiness_check:
        print(f"Missing readiness artifact: {args.readiness}", file=sys.stderr)
        return 2

    if not args.skip_readiness_check and not overall_ok:
        print(
            "Readiness overall_ok is false; fix policy chain or use --skip-readiness-check (dev only).",
            file=sys.stderr,
        )
        exec_status = "blocked_readiness"
        exit_code = 3
    else:
        exec_status = "dry_run_ok" if args.dry_run else "plan_recorded"
        exit_code = 0

    theology_ok = args.theology_baseline.is_file()
    bundle_ok = args.bundle_json.is_file()

    doc = {
        "schema": ARTIFACT_SCHEMA,
        "version": VERSION,
        "ts_utc": ts,
        "hypothesis_tier": "B",
        "non_gating_ack": True,
        "job_id": job_id,
        "readiness": {
            "artifact_path": _rel(args.readiness),
            "overall_ok": overall_ok if args.readiness.is_file() else None,
            "snapshot_ts_utc": readiness_doc.get("ts_utc"),
            "skipped_check": args.skip_readiness_check,
        },
        "inputs": {
            "theology_baseline_path": _rel(args.theology_baseline),
            "theology_baseline_exists": theology_ok,
            "corpus_graph_bundle_path": _rel(args.bundle_json),
            "corpus_graph_bundle_exists": bundle_ok,
        },
        "execution": {
            "status": exec_status,
            "llm_invoked": False,
            "llm_placeholder_requested": bool(args.allow_llm_placeholder),
            "dry_run": bool(args.dry_run),
            "next_steps": [
                "Implement retrieval/index builders under LOGOS_VECTOR_INDEX_POLICY_V1 when status=active.",
                "Optional: wire explicit LLM/RAG module behind separate CLI flag and budget caps.",
            ],
        },
        "notes": "No external API calls in this runner; Track B observation only.",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.dry_run:
        print(f"job_id={job_id} status={exec_status} write={_rel(args.output)}")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
