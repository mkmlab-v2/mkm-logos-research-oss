#!/usr/bin/env python3
"""Track B deep fusion job v1 — skeleton only.

Requires logos_track_b_policy_readiness_v1 overall_ok unless --skip-readiness-check.
Does not call LLM/embeddings; records inputs and execution status for offline audits.
"""
from __future__ import annotations

import argparse
import json
import subprocess
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
DISTILL_RUNNER = ROOT / "scripts" / "run_lens_logos_deep_fusion.py"

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
    ap.add_argument(
        "--write-distill-template",
        type=Path,
        default=None,
        metavar="PATH",
        help="After successful gate, run run_lens_logos_deep_fusion.py --bundle-json --write-template (no LLM).",
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

    distill_out: dict[str, Any] = {"skipped": True, "reason": None}
    final_exit = exit_code

    if (
        args.write_distill_template is not None
        and exit_code == 0
        and bundle_ok
        and DISTILL_RUNNER.is_file()
    ):
        cp = subprocess.run(
            [
                sys.executable,
                str(DISTILL_RUNNER),
                "--bundle-json",
                str(args.bundle_json.resolve()),
                "--build-id",
                job_id,
                "--slice-id",
                "slice5_track_b_chain",
                "--write-template",
                str(args.write_distill_template.resolve()),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        distill_out = {
            "skipped": False,
            "distill_runner": _rel(DISTILL_RUNNER),
            "template_path": _rel(args.write_distill_template),
            "subprocess_exit_code": cp.returncode,
            "stderr_tail": (cp.stderr or "")[-500:],
        }
        doc["outputs"] = {"distill_template": distill_out}
        if cp.returncode != 0:
            doc["execution"]["distill_template_failed"] = True
            final_exit = 4
        else:
            doc["execution"]["distill_template_written"] = True
    elif args.write_distill_template is not None:
        reason = "blocked_readiness_or_bad_gate" if exit_code != 0 else "bundle_missing_or_runner_missing"
        distill_out = {"skipped": True, "reason": reason}
        doc["outputs"] = {"distill_template": distill_out}

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.dry_run:
        print(f"job_id={job_id} status={exec_status} write={_rel(args.output)}")

    return final_exit


if __name__ == "__main__":
    raise SystemExit(main())
