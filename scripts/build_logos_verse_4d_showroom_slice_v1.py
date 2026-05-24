#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emit Track B showroom thin slice for Logos verse 4D factory (v1_core_subset).

Reads existing artifacts only (no heavy recompute). Validates against
docs/final/schemas/logos_verse_4d_showroom_slice_v1.schema.json on write.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_COVERAGE_DIFF = (
    ROOT / "reports/constitution/btrack_pilot/logos_verse_canon_coverage_diff_v1_latest.json"
)
DEFAULT_MEDOIDS = ROOT / "docs/final/artifacts/logos_verse_4d_medoids_v1_latest.json"
DEFAULT_OS_COMPARE = ROOT / "docs/final/artifacts/logos_verse_4d_os_compare_v1_latest.json"
DEFAULT_CORPUS = ROOT / "docs/final/artifacts/logos_verse_4d_corpus_v1_latest.json"
DEFAULT_CONTRACT = ROOT / "docs/final/artifacts/LOGOS_VERSE_4D_V1_CONTRACT.json"
DEFAULT_CROSS_BRIDGE = ROOT / "docs/final/artifacts/logos_verse_myeongri_cross_bridge_v1_latest.json"
DEFAULT_CROSS_BRIDGE_MATRIX = (
    ROOT / "docs/final/artifacts/logos_verse_myeongri_cross_bridge_matrix_v1_latest.json"
)
CROSS_BRIDGE_CMD = "py scripts/build_logos_verse_myeongri_cross_bridge_v1.py"
DEFAULT_SCHEMA = ROOT / "docs/final/schemas/logos_verse_4d_showroom_slice_v1.schema.json"
DEFAULT_OUT_ARTIFACTS = ROOT / "docs/final/artifacts/logos_verse_4d_showroom_slice_v1_latest.json"
DEFAULT_OUT_SHOWROOM = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "showroom_logos_verse_4d_slice_v1.json"
)

VERSION = "1.0.0"
SUBSET_ID = "v1_core_subset"
PUBLIC_FACING_POINTER = "docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md"
ONE_LINE_REPRODUCE = "py scripts/run_logos_verse_4d_track_b_full_chain_v1.py"

DISCLAIMER_NOTE_KO = (
    "구절 4D OS 팩토리 연구 스냅샷([HYPO])입니다. 우주 OS 증명·Track A 압축 승격·"
    "실매매·임상 게이트 근거가 아닙니다."
)

SAMPLE_SIZE_SMALL_THRESHOLD = 1000


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def _validate(doc: dict[str, Any], schema_path: Path) -> None:
    jsonschema = __import__("jsonschema")
    schema = _load(schema_path)
    jsonschema.Draft7Validator(schema).validate(doc)


def _phase_runners(contract: dict[str, Any]) -> list[dict[str, str]]:
    pipelines = contract.get("pipelines") or {}
    out: list[dict[str, str]] = []
    for phase_key in (
        "phase1_canonical_corpus",
        "phase2_graph_and_medoid",
        "phase3_lexicon_back_projection",
        "phase4_external_proof",
    ):
        block = pipelines.get(phase_key)
        if not isinstance(block, dict):
            continue
        runner = block.get("runner")
        if not isinstance(runner, str) or not runner.strip():
            continue
        row: dict[str, str] = {"phase": phase_key, "runner": runner.replace("\\", "/")}
        desc = block.get("description")
        if isinstance(desc, str) and desc.strip():
            row["description"] = desc.strip()
        out.append(row)
    return out


def _forbidden_claims(contract: dict[str, Any]) -> list[str]:
    phase4 = (contract.get("pipelines") or {}).get("phase4_external_proof") or {}
    claims = phase4.get("forbidden_claims")
    if isinstance(claims, list) and claims:
        return [str(c) for c in claims]
    return [
        "proven_cosmic_os",
        "perfect_match_only_bible",
        "track_a_compression_auto_upgrade",
    ]


def _boundary_sentences(contract: dict[str, Any], coverage_diff: dict[str, Any]) -> tuple[str, str]:
    bs = contract.get("boundary_sentences")
    if isinstance(bs, dict):
        ko = bs.get("ko")
        en = bs.get("en")
        if isinstance(ko, str) and ko.strip() and isinstance(en, str) and en.strip():
            return ko.strip(), en.strip()
    interp = coverage_diff.get("interpretation") or {}
    ko_fb = interp.get("accurate_framing_ko")
    if isinstance(ko_fb, str) and ko_fb.strip():
        counts = coverage_diff.get("counts") or {}
        en_fb = (
            f"MT canon SSOT {counts.get('full_canon_verse_count', '?')} verses vs "
            f"verse_decoded_v2 (BHS+SBLGNT) {counts.get('verse_decoded_v2_count', '?')}; "
            f"gap {counts.get('gap_count', '?')} is upstream coverage, not Phase-1 drops."
        )
        return ko_fb.strip(), en_fb
    raise ValueError("boundary sentences missing in contract and coverage diff")


def _cross_bridge_summary(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    doc = _load(path)
    geom = doc.get("geometry") or {}
    return {
        "report_path": _rel(path),
        "verse_id": (doc.get("verse_os") or {}).get("verse_id"),
        "human_profile_id": (doc.get("human_terminal") or {}).get("profile_id"),
        "l2_os_human": geom.get("l2_os_human"),
        "cosine_os_human": geom.get("cosine_os_human"),
        "one_line_cmd": CROSS_BRIDGE_CMD,
        "pedagogical_map": doc.get("pedagogical_map"),
        "interpretation_note": doc.get("interpretation_note"),
    }


def _cross_bridge_matrix_summary(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    doc = _load(path)
    profiles = doc.get("human_profiles") or []
    if not profiles and isinstance(doc.get("human_terminal"), dict):
        profiles = [doc["human_terminal"]]
    summary = doc.get("summary") or {}
    return {
        "report_path": _rel(path),
        "matrix_version": doc.get("version"),
        "top_n": len(doc.get("rows") or []),
        "human_profile_ids": [p.get("profile_id") for p in profiles if isinstance(p, dict)],
        "unique_verse_vector_4d_count": summary.get("unique_verse_vector_4d_count"),
        "vector_4d_collapse_note": summary.get("vector_4d_collapse_note"),
        "rows": doc.get("rows") or [],
    }


def build_slice(
    *,
    coverage_diff: dict[str, Any],
    medoids: dict[str, Any],
    os_compare: dict[str, Any],
    corpus: dict[str, Any],
    contract: dict[str, Any],
    cross_bridge: dict[str, Any] | None = None,
    cross_bridge_matrix: dict[str, Any] | None = None,
    source_paths: dict[str, Path] | None = None,
) -> dict[str, Any]:
    boundary_ko, boundary_en = _boundary_sentences(contract, coverage_diff)
    diff_counts = coverage_diff.get("counts") or {}
    corpus_counts = corpus.get("counts") or {}
    interp = coverage_diff.get("interpretation") or {}

    top_medoids_raw = medoids.get("global_medoids") or []
    top_medoids: list[dict[str, Any]] = []
    for row in top_medoids_raw[:10]:
        if not isinstance(row, dict):
            continue
        top_medoids.append(
            {
                "rank": int(row["rank"]),
                "verse_id": str(row["verse_id"]),
                "centrality": float(row["centrality"]),
            }
        )

    build_os = os_compare.get("build") or {}
    sample_size = int(build_os.get("sample_size") or 0)
    max_rows = int(build_os.get("max_rows") or 0)
    full_graph = bool(build_os.get("full_graph"))
    canon_entry = next(
        (c for c in (os_compare.get("corpora") or []) if isinstance(c, dict) and c.get("label") == "canon"),
        None,
    )
    canon_mean = canon_entry.get("mean_top1_cosine") if isinstance(canon_entry, dict) else None

    sample_small = sample_size < SAMPLE_SIZE_SMALL_THRESHOLD or (
        max_rows > 0 and max_rows < SAMPLE_SIZE_SMALL_THRESHOLD
    )
    phase4_block: dict[str, Any] = {
        "summary": {
            "sample_size": sample_size,
            "max_rows": max_rows,
            "full_graph": full_graph,
            "canon_mean_top1_cosine": canon_mean,
            "interpretation_note": str(os_compare.get("interpretation_note") or ""),
        },
        "deltas_vs_canon": dict(os_compare.get("deltas_vs_canon") or {}),
        "sample_size_small": sample_small,
    }
    if sample_small:
        phase4_block["sample_size_small_note"] = (
            f"Phase-4 OS compare used sample_size={sample_size}, max_rows={max_rows}; "
            "deltas are illustrative only, not full-corpus proof."
        )

    doc: dict[str, Any] = {
        "schema": "logos_verse_4d_showroom_slice_v1",
        "version": VERSION,
        "subset_id": SUBSET_ID,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "boundary_sentence_ko": boundary_ko,
        "boundary_sentence_en": boundary_en,
        "coverage": {
            "full_canon_verse_count": int(diff_counts.get("full_canon_verse_count") or 0),
            "verse_decoded_v2_count": int(diff_counts.get("verse_decoded_v2_count") or 0),
            "gap_count": int(diff_counts.get("gap_count") or 0),
            "intersection_count": int(diff_counts.get("intersection_count") or 0),
            "only_in_v2_count": int(diff_counts.get("only_in_v2_count") or 0),
            "phase1_rows_emitted": int(corpus_counts.get("rows_emitted") or 0),
            "phase1_rows_dropped": int(interp.get("phase1_logos_verse_4d_rows_dropped") or 0),
            "gap_cause": str(interp.get("gap_cause") or "upstream_coverage_not_phase1_filter"),
            "verse_decoded_v2_editions": dict(coverage_diff.get("verse_decoded_v2_editions") or {}),
            "gap_by_testament": dict(coverage_diff.get("gap_by_testament") or {}),
        },
        "factory_demo": {
            "one_line_reproduce_cmd": ONE_LINE_REPRODUCE,
            "phase_runners": _phase_runners(contract),
            "contract_path": _rel((source_paths or {}).get("contract", DEFAULT_CONTRACT)),
            "forbidden_claims": _forbidden_claims(contract),
        },
        "sample_findings": {
            "top_medoids": top_medoids,
            "phase4_null_vs_canon": phase4_block,
        },
        "disclaimer": {
            "evidence_tier": "hypo_research_only",
            "gating_status": "NON_GATING",
            "ready_for_external_send": False,
            "note_ko": DISCLAIMER_NOTE_KO,
        },
        "track_wall": {
            "a_track_auto_promotion": False,
            "live_trading_trigger": False,
        },
        "public_facing_pointer": PUBLIC_FACING_POINTER,
        "source_artifacts": {
            "coverage_diff": _rel((source_paths or {}).get("coverage_diff", DEFAULT_COVERAGE_DIFF)),
            "medoids": _rel((source_paths or {}).get("medoids", DEFAULT_MEDOIDS)),
            "os_compare": _rel((source_paths or {}).get("os_compare", DEFAULT_OS_COMPARE)),
            "corpus_manifest": _rel((source_paths or {}).get("corpus", DEFAULT_CORPUS)),
            "contract": _rel((source_paths or {}).get("contract", DEFAULT_CONTRACT)),
        },
    }
    if cross_bridge is not None:
        doc["cross_bridge_v0"] = cross_bridge
    if cross_bridge_matrix is not None:
        doc["cross_bridge_matrix_v0"] = cross_bridge_matrix
    return doc


def _write_outputs(doc: dict[str, Any], paths: list[Path], schema_path: Path) -> None:
    _validate(doc, schema_path)
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    for out_path in paths:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--coverage-diff", type=Path, default=DEFAULT_COVERAGE_DIFF)
    ap.add_argument("--medoids", type=Path, default=DEFAULT_MEDOIDS)
    ap.add_argument("--os-compare", type=Path, default=DEFAULT_OS_COMPARE)
    ap.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    ap.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    ap.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT_ARTIFACTS)
    ap.add_argument(
        "--mirror-showroom",
        type=Path,
        default=DEFAULT_OUT_SHOWROOM,
        help="Second output path for jemaai-cloud-mvp deploy mirror.",
    )
    ap.add_argument("--no-mirror", action="store_true", help="Skip mirror showroom path.")
    ap.add_argument("--cross-bridge", type=Path, default=DEFAULT_CROSS_BRIDGE)
    ap.add_argument("--cross-bridge-matrix", type=Path, default=DEFAULT_CROSS_BRIDGE_MATRIX)
    args = ap.parse_args()

    required = [
        ("schema", args.schema),
        ("coverage diff", args.coverage_diff),
        ("medoids", args.medoids),
        ("os compare", args.os_compare),
        ("corpus manifest", args.corpus),
        ("contract", args.contract),
    ]
    for label, path in required:
        if not path.is_file():
            print(f"missing {label}: {path}", file=sys.stderr)
            return 2

    try:
        paths = {
            "coverage_diff": args.coverage_diff,
            "medoids": args.medoids,
            "os_compare": args.os_compare,
            "corpus": args.corpus,
            "contract": args.contract,
        }
        doc = build_slice(
            coverage_diff=_load(args.coverage_diff),
            medoids=_load(args.medoids),
            os_compare=_load(args.os_compare),
            corpus=_load(args.corpus),
            contract=_load(args.contract),
            cross_bridge=_cross_bridge_summary(args.cross_bridge),
            cross_bridge_matrix=_cross_bridge_matrix_summary(args.cross_bridge_matrix),
            source_paths=paths,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"build failed: {exc}", file=sys.stderr)
        return 1

    outputs = [args.out_json]
    if not args.no_mirror and args.mirror_showroom:
        outputs.append(args.mirror_showroom)

    try:
        _write_outputs(doc, outputs, args.schema)
    except Exception as exc:  # noqa: BLE001
        print(f"validate/write failed: {exc}", file=sys.stderr)
        return 3

    for out_path in outputs:
        print(f"Wrote {_rel(out_path)} medoids={len(doc['sample_findings']['top_medoids'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
