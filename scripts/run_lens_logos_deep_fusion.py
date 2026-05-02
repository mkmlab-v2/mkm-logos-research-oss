#!/usr/bin/env python3
"""Logos deep fusion — Track B placeholder (no LLM, no graph query).

Real heavy RAG / KG traversal belongs in offline batch jobs per
docs/final/LOGOS_DEEP_RESEARCH_TRACK_B_BACKLOG_V1.md. This CLI validates
contract paths and can emit a minimal schema-valid distill template.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "final" / "artifacts" / "LOGOS_DEEP_RESEARCH_DISTILL_CONTRACT_V1.json"
SCHEMA = ROOT / "docs" / "final" / "schemas" / "logos_deep_research_distill_v1.schema.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "logos_deep_research_distill_latest.json"

ARTIFACT_SCHEMA = "logos_deep_research_distill_v1"
VERSION = "1.0.1"


def _manifest_digest(paths: list[Path]) -> str:
    h = hashlib.sha256()
    for p in sorted(paths, key=lambda x: str(x)):
        h.update(str(p.resolve()).encode("utf-8"))
        if p.is_file():
            h.update(p.read_bytes())
    return "sha256:" + h.hexdigest()


def _minimal_distill_template(
    build_id: str,
    slice_id: str,
    provenance_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    doc: dict[str, Any] = {
        "schema": ARTIFACT_SCHEMA,
        "version": VERSION,
        "ts_utc": now,
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "non_gating_ack": True,
        "build_id": build_id,
        "source_slice": {"slice_id": slice_id, "description": "placeholder", "row_count": 0},
        "state_vector_logos": {
            "mean_4d": {"S": 0.0, "L": 0.0, "K": 0.0, "M": 0.0},
        },
        "epistemic_uncertainty": 1.0,
        "veto_flags": {
            "insufficient_evidence": True,
            "batch_too_small": True,
            "hash_coverage_below_min": True,
            "policy_violation": False,
        },
        "evidence_refs": [],
        "provenance": {
            "input_manifest_sha256": "placeholder_not_a_real_build",
            "runner": "scripts/run_lens_logos_deep_fusion.py",
            "notes": "Template only — replace with real ingest manifest hash after slice 1+.",
        },
        "review_gate": {
            "status": "pending",
            "reason_code": "template_placeholder",
        },
    }
    if provenance_extra:
        doc["provenance"].update(provenance_extra)
    return doc


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _provenance_track_b_optionals(
    vector_manifest: Path | None,
    ann_lite_report: Path | None,
    ann_lite_query_smoke: Path | None,
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if vector_manifest is not None and vector_manifest.is_file():
        out["track_b_vector_manifest_path"] = str(vector_manifest.resolve())
        out["track_b_vector_manifest_sha256"] = _file_sha256(vector_manifest)
    if ann_lite_report is not None and ann_lite_report.is_file():
        out["track_b_ann_lite_report_path"] = str(ann_lite_report.resolve())
        out["track_b_ann_lite_report_sha256"] = _file_sha256(ann_lite_report)
    if ann_lite_query_smoke is not None and ann_lite_query_smoke.is_file():
        out["track_b_ann_lite_query_smoke_path"] = str(ann_lite_query_smoke.resolve())
        out["track_b_ann_lite_query_smoke_sha256"] = _file_sha256(ann_lite_query_smoke)
    return out


def _provenance_from_bundle(bundle_path: Path) -> dict[str, Any]:
    """Fill provenance fields from logos_corpus_graph_bundle_v1 JSON."""
    raw = json.loads(bundle_path.read_text(encoding="utf-8"))
    if raw.get("schema") != "logos_corpus_graph_bundle_v1":
        raise ValueError("bundle schema must be logos_corpus_graph_bundle_v1")
    snap = raw.get("manifest_snapshot") or {}
    dedupe = raw.get("dedupe_bundle_key_sha256")
    if not isinstance(dedupe, str) or len(dedupe) != 64:
        raise ValueError("bundle missing dedupe_bundle_key_sha256")
    corp_sha = snap.get("corpus_input_sha256")
    if not isinstance(corp_sha, str) or len(corp_sha) != 64:
        raise ValueError("bundle.manifest_snapshot missing corpus_input_sha256")
    out: dict[str, Any] = {
        "input_manifest_sha256": corp_sha,
        "corpus_graph_bundle_path": str(bundle_path.resolve()),
        "dedupe_bundle_key_sha256": dedupe,
        "notes": "provenance anchored to slice 2 bundle + corpus digest",
    }
    mfs = snap.get("manifest_file_sha256")
    if isinstance(mfs, str) and len(mfs) == 64:
        out["manifest_file_sha256"] = mfs
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate contract/schema files exist; exit 0.",
    )
    ap.add_argument(
        "--emit-template",
        action="store_true",
        help="Print minimal JSON distill document to stdout (placeholder).",
    )
    ap.add_argument(
        "--write-template",
        type=Path,
        metavar="PATH",
        help="Write minimal template JSON to PATH.",
    )
    ap.add_argument("--build-id", default="dry_run_v1", help="build_id field")
    ap.add_argument("--slice-id", default="slice0_contract_only", help="source_slice.slice_id")
    ap.add_argument(
        "--bundle-json",
        type=Path,
        default=None,
        metavar="PATH",
        help="Optional logos_corpus_graph_bundle_v1 JSON — anchors distill provenance (slice 2).",
    )
    ap.add_argument(
        "--vector-manifest-json",
        type=Path,
        default=None,
        metavar="PATH",
        help="Optional logos_vector_index_manifest_v1 JSON (path + sha256 into provenance).",
    )
    ap.add_argument(
        "--ann-lite-report-json",
        type=Path,
        default=None,
        metavar="PATH",
        help="Optional ANN lite build report JSON.",
    )
    ap.add_argument(
        "--ann-lite-query-smoke-json",
        type=Path,
        default=None,
        metavar="PATH",
        help="Optional query smoke JSON from query_logos_vector_index_ann_lite_v1.py.",
    )
    args = ap.parse_args()

    if not CONTRACT.is_file():
        print(f"Missing contract: {CONTRACT}", file=sys.stderr)
        return 2
    if not SCHEMA.is_file():
        print(f"Missing schema: {SCHEMA}", file=sys.stderr)
        return 2

    meta = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if meta.get("artifact_schema") != ARTIFACT_SCHEMA:
        print("Contract artifact_schema mismatch.", file=sys.stderr)
        return 2

    digest = _manifest_digest([CONTRACT, SCHEMA])

    provenance_extra: dict[str, Any] | None = None
    if args.bundle_json is not None:
        if not args.bundle_json.is_file():
            print(f"Missing bundle JSON: {args.bundle_json}", file=sys.stderr)
            return 2
        try:
            provenance_extra = _provenance_from_bundle(args.bundle_json)
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 2

    track_b_opt = _provenance_track_b_optionals(
        args.vector_manifest_json,
        args.ann_lite_report_json,
        args.ann_lite_query_smoke_json,
    )

    if args.emit_template or args.write_template is not None:
        merged = dict(provenance_extra) if provenance_extra else {}
        merged.update(track_b_opt)
        doc = _minimal_distill_template(args.build_id, args.slice_id, merged if merged else None)
        if provenance_extra is None:
            doc["provenance"]["input_manifest_sha256"] = digest
        text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
        if args.write_template is not None:
            args.write_template.parent.mkdir(parents=True, exist_ok=True)
            args.write_template.write_text(text, encoding="utf-8")
        if args.emit_template:
            sys.stdout.write(text)
        return 0

    if args.dry_run:
        print(f"OK contract={CONTRACT.name} schema={SCHEMA.name} manifest={digest}")
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
