#!/usr/bin/env python3
"""Build public-safe academic abstract + outline draft from evidence bundle."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def _resolve(root: Path, path_str: str) -> Path:
    p = Path(path_str)
    if not p.is_absolute():
        p = root / p
    return p


def main() -> int:
    ap = argparse.ArgumentParser(description="Build two-track submission draft.")
    ap.add_argument("--repo-root", default=str(ROOT))
    ap.add_argument(
        "--evidence-json",
        default="docs/final/artifacts/two_track_submission_evidence_bundle_latest.json",
    )
    ap.add_argument(
        "--readiness-json",
        default="docs/final/artifacts/two_track_raw_oos_readiness_latest.json",
    )
    ap.add_argument(
        "--significance-json",
        default="docs/final/artifacts/two_track_statistical_significance_report_latest.json",
    )
    ap.add_argument(
        "--benchmark-json",
        default="docs/final/artifacts/two_track_benchmark_comparison_latest.json",
    )
    ap.add_argument(
        "--public-safe-json",
        default="docs/final/artifacts/two_track_public_safe_report_latest.json",
    )
    ap.add_argument("--output-json", default="docs/final/artifacts/two_track_submission_draft_latest.json")
    args = ap.parse_args()

    repo_root = Path(args.repo_root)
    if not repo_root.is_absolute():
        repo_root = ROOT / repo_root
    repo_root = repo_root.resolve()
    evidence_path = _resolve(repo_root, args.evidence_json)
    readiness_path = _resolve(repo_root, args.readiness_json)
    significance_path = _resolve(repo_root, args.significance_json)
    benchmark_path = _resolve(repo_root, args.benchmark_json)
    public_safe_path = _resolve(repo_root, args.public_safe_json)
    if not evidence_path.is_file():
        raise SystemExit(f"missing required input json: {evidence_path}")

    evidence = _load(evidence_path)
    readiness = _load(readiness_path) if readiness_path.is_file() else {}
    significance = _load(significance_path) if significance_path.is_file() else {}
    benchmark = _load(benchmark_path) if benchmark_path.is_file() else {}

    gates = evidence.get("gates") if isinstance(evidence.get("gates"), dict) else {}
    readiness_summary = readiness.get("summary") if isinstance(readiness.get("summary"), dict) else {}
    sig_interp = significance.get("significance_interpretation")
    sig_interp_str = str(sig_interp) if isinstance(sig_interp, str) and sig_interp.strip() else "see significance report"

    primary_delta = ((benchmark.get("delta") or {}).get("shift_score", 0.0)) if isinstance(benchmark, dict) else 0.0
    try:
        primary_delta_num = float(primary_delta)
    except Exception:
        primary_delta_num = 0.0

    publication_ready = bool(readiness_summary.get("ready_for_publication_claim", False))
    if not readiness_path.is_file():
        publication_ready = bool(gates.get("ready_for_publication_claim", False))
    bundle_ready = bool(gates.get("bundle_ready", False))
    boundary = (
        "Public-safe disclosure only: core theory formula/weights/tuning internals remain redacted."
    )

    title_candidates = [
        "Two-Track Safety-Gated Inference: A Public-Safe Falsification Architecture for Meaning-Driven Signals",
        "From Meaning Graph to Survivorship Gate: A Reproducible Two-Track Validation Stack",
        "Public-Safe Alpha Governance: Two-Track Evidence Design with Raw OOS Readiness",
    ]
    chosen_title = title_candidates[0] if publication_ready and bundle_ready else title_candidates[1]

    abstract = {
        "problem": (
            "Meaning-rich cross-reference signals are expressive but prone to overfitting and false discovery "
            "when promoted directly to trading decisions."
        ),
        "method": (
            "We separate K-track (knowledge/IP narrative layer) from T-track (survivor filter and rollback gates), "
            "and evaluate claims with falsification suite, multi-baseline comparison, and bootstrap/permutation significance."
        ),
        "result": (
            f"Current evidence bundle reports bundle_ready={bundle_ready}, publication_ready={publication_ready}, "
            f"primary_delta_shift_score={primary_delta_num:.4f}, interpretation='{sig_interp_str}'."
        ),
        "claim_boundary": boundary,
    }

    outline = [
        "1) Introduction: Why meaning-network signals require safety-first promotion gates",
        "2) Two-Track Architecture: K-track narrative layer vs T-track survivorship layer",
        "3) Experimental Protocol: raw OOS policy, falsification checks, multi-baseline setup",
        "4) Results: benchmark deltas, significance interpretation, readiness status",
        "5) Governance & Disclosure: rollback contract, public-safe redaction policy",
        "6) Limitations & Next Steps: drift horizon extension and external replication plan",
    ]

    draft = {
        "schema": "two_track_submission_draft_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "title_candidates": title_candidates,
        "recommended_title": chosen_title,
        "abstract_scaffold_en": abstract,
        "section_outline_en": outline,
        "submission_gate_snapshot": {
            "bundle_ready": bundle_ready,
            "ready_for_publication_claim": publication_ready,
            "missing_artifacts": gates.get("missing_artifacts", []),
        },
        "public_safe_boundary": boundary,
        "sources": {
            "evidence_json": str(evidence_path),
            "readiness_json": str(readiness_path) if readiness_path.is_file() else None,
            "significance_json": str(significance_path) if significance_path.is_file() else None,
            "benchmark_json": str(benchmark_path) if benchmark_path.is_file() else None,
            "public_safe_json": str(public_safe_path) if public_safe_path.is_file() else None,
        },
        "degraded_mode": {
            "enabled": (not readiness_path.is_file())
            or (not significance_path.is_file())
            or (not benchmark_path.is_file())
            or (not public_safe_path.is_file()),
            "missing_inputs": [
                str(p)
                for p in (readiness_path, significance_path, benchmark_path, public_safe_path)
                if not p.is_file()
            ],
        },
    }

    out_path = _resolve(repo_root, args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(draft, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
