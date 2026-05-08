#!/usr/bin/env python3
"""Cross-platform Track B Logos pipeline chain (readiness → manifest → optional ANN lite → job → distill).

Mirrors scripts/Run-LogosTrackBChainV1.ps1 for Linux/Mac/CI. No LLM calls.

Unknown CLI tokens are forwarded to run_logos_track_b_deep_fusion_job_v1.py (parse_known_args).
Example:  %(prog)s --skip-distill --output /tmp/job.json --dry-run
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "docs/final/artifacts/LOGOS_VECTOR_INDEX_POLICY_V1.json"


def _run(script: str, argv: list[str]) -> int:
    cmd = [sys.executable, str(ROOT / script)] + argv
    return subprocess.run(cmd, cwd=str(ROOT)).returncode


def _normalize_job_extra(argv: list[str]) -> list[str]:
    """Drop optional `--` separator before forwarding extra args to child job."""
    return [tok for tok in argv if tok != "--"]


def _ann_lite_args_from_policy() -> list[str]:
    if not POLICY_PATH.is_file():
        return []
    try:
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if policy.get("status") != "active":
        return []
    emb = policy.get("embedding")
    if not isinstance(emb, dict):
        return []
    model_id = emb.get("model_id")
    if not isinstance(model_id, str) or not model_id.strip():
        return []
    return [
        "--embedding-backend",
        "sentence_transformers",
        "--sentence-transformer-model",
        model_id.strip(),
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--skip-readiness-report",
        action="store_true",
        help="Skip report_logos_track_b_policy_readiness_v1.py",
    )
    ap.add_argument(
        "--skip-distill",
        action="store_true",
        help="Do not pass --write-distill-template to deep fusion job",
    )
    ap.add_argument(
        "--include-ann-lite",
        action="store_true",
        help="Run hash_stub ANN lite build after manifest",
    )
    ap.add_argument(
        "--skip-ann-lite-query-smoke",
        action="store_true",
        help="With --include-ann-lite, skip query_logos_vector_index_ann_lite_v1 smoke",
    )
    ap.add_argument(
        "--skip-freshness-sidecar",
        action="store_true",
        help="Skip build_logos_track_c_freshness_sidecar_v1.py after deep fusion job",
    )
    args, job_extra = ap.parse_known_args()
    job_extra = _normalize_job_extra(job_extra)

    if not args.skip_readiness_report:
        rc = _run("scripts/report_logos_track_b_policy_readiness_v1.py", [])
        if rc != 0:
            return rc

    rc = _run("scripts/build_logos_vector_index_manifest_v1.py", [])
    if rc != 0:
        return rc

    if args.include_ann_lite:
        ann_args = _ann_lite_args_from_policy()
        rc = _run("scripts/build_logos_vector_index_ann_lite_v1.py", ann_args)
        if rc != 0:
            return rc
        if not args.skip_ann_lite_query_smoke:
            sqlite_ann = ROOT / "docs/final/artifacts/logos_vector_index_ann_lite_v1.sqlite"
            smoke_json = ROOT / "docs/final/artifacts/logos_vector_ann_lite_query_smoke_latest.json"
            smoke_json.parent.mkdir(parents=True, exist_ok=True)
            smoke_args = [
                "--sqlite",
                str(sqlite_ann),
                "--query",
                "track_b_pipeline_smoke_v1",
                "--top-k",
                "3",
                "--output-json",
                str(smoke_json),
            ]
            if ann_args:
                smoke_args += ["--sentence-transformer-model", ann_args[-1]]
            rc = _run(
                "scripts/query_logos_vector_index_ann_lite_v1.py",
                smoke_args,
            )
            if rc != 0:
                return rc

    distill_path = ROOT / "docs/final/artifacts/logos_deep_research_distill_track_b_chain_v1_latest.json"
    job_argv: list[str] = list(job_extra)
    if not args.skip_distill:
        distill_path.parent.mkdir(parents=True, exist_ok=True)
        job_argv += ["--write-distill-template", str(distill_path)]

    rc = _run("scripts/run_logos_track_b_deep_fusion_job_v1.py", job_argv)
    if rc != 0:
        return rc
    if args.skip_freshness_sidecar:
        return 0
    return _run("scripts/build_logos_track_c_freshness_sidecar_v1.py", [])


if __name__ == "__main__":
    raise SystemExit(main())
