#!/usr/bin/env python3
"""B-track satellite orbit drift report — canonical medoid vs DSS/apocrypha paths (no row merge)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_CORPUS_MANIFEST = ROOT / "docs/final/artifacts/logos_verse_4d_single_anchor_corpus_v1_latest.json"
DEFAULT_MEDOIDS = ROOT / "docs/final/artifacts/logos_verse_4d_single_anchor_medoids_v1_latest.json"
DEFAULT_COVERAGE = (
    ROOT / "reports/constitution/btrack_pilot/logos_verse_canon_coverage_diff_complete_v1_latest.json"
)
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_satellite_orbit_drift_v1_latest.json"
DEFAULT_DRIFT_METRICS = ROOT / "docs/final/artifacts/logos_satellite_drift_metrics_v1_latest.json"
DEFAULT_KNN_DRIFT = ROOT / "docs/final/artifacts/logos_satellite_knn_drift_v1_latest.json"
DEFAULT_KNN_PACK = ROOT / "docs/final/artifacts/logos_satellite_knn_drift_pack_v1_latest.json"

SATELLITE_CANDIDATES = [
    {
        "corpus_type": "apocrypha",
        "jsonl": "reports/constitution/btrack_pilot/logos_verse_4d_apocrypha_lane_v1_latest.jsonl",
        "contract_ref": "docs/final/artifacts/LOGOS_VERSE_4D_V1_CONTRACT.json",
    },
    {
        "corpus_type": "dss",
        "jsonl": "reports/constitution/btrack_pilot/logos_verse_4d_dss_lane_v1_latest.jsonl",
        "enriched_jsonl": "data/logos/manuscripts/dss_parsed_enriched.jsonl",
        "manifest_ref": "docs/final/artifacts/logos_dss_enriched_manifest_v1_latest.json",
        "lane_manifest_ref": "docs/final/artifacts/logos_dss_satellite_lane_manifest_v1_latest.json",
        "slot_mapping_ref": "docs/final/artifacts/logos_dss_crossref_slot_mapping_v1_latest.json",
        "strict_gate_audit_ref": "docs/final/artifacts/logos_dss_crossref_strict_gate_audit_v1_latest.json",
        "slot_mapping_refresh_pack_ref": "docs/final/artifacts/logos_dss_slot_mapping_refresh_pack_v1_latest.json",
        "draft_ref": "docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json",
    },
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    resolved = path.resolve()
    root = ROOT.resolve()
    if resolved == root or root in resolved.parents:
        return str(resolved.relative_to(root)).replace("\\", "/")
    return str(resolved.as_posix())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus-manifest", type=Path, default=DEFAULT_CORPUS_MANIFEST)
    ap.add_argument("--medoids-json", type=Path, default=DEFAULT_MEDOIDS)
    ap.add_argument("--coverage-diff", type=Path, default=DEFAULT_COVERAGE)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--drift-metrics-json", type=Path, default=DEFAULT_DRIFT_METRICS)
    ap.add_argument("--knn-drift-json", type=Path, default=DEFAULT_KNN_DRIFT)
    ap.add_argument("--knn-drift-pack-json", type=Path, default=DEFAULT_KNN_PACK)
    args = ap.parse_args()

    knn_pack: dict[str, Any] | None = None
    if args.knn_drift_pack_json.is_file():
        knn_pack = json.loads(args.knn_drift_pack_json.read_text(encoding="utf-8"))

    medoid_id = None
    if args.medoids_json.is_file():
        med = json.loads(args.medoids_json.read_text(encoding="utf-8"))
        medoid_id = med.get("top_global_medoid") or med.get("global_medoid_verse_id")
        if not medoid_id:
            globals_ = med.get("global_medoids")
            if isinstance(globals_, list) and globals_:
                first = globals_[0]
                if isinstance(first, dict):
                    medoid_id = first.get("verse_id")

    coverage_gap = None
    if args.coverage_diff.is_file():
        coverage_gap = json.loads(args.coverage_diff.read_text(encoding="utf-8")).get("counts", {}).get(
            "gap_count"
        )

    satellites: list[dict[str, Any]] = []
    for spec in SATELLITE_CANDIDATES:
        row: dict[str, Any] = {
            "corpus_type": spec["corpus_type"],
            "source_track": "B_ext",
            "merge_into_canon_forbidden": True,
            "drift_metrics": {"status": "pending_ingest"},
        }
        if spec.get("jsonl"):
            p = ROOT / spec["jsonl"]
            row["jsonl"] = _rel(p)
            row["jsonl_present"] = p.is_file()
            if p.is_file():
                sat_knn: dict[str, Any] | None = None
                if knn_pack and isinstance(knn_pack.get("satellites"), dict):
                    sat_knn = knn_pack["satellites"].get(spec["corpus_type"])
                if sat_knn and sat_knn.get("vectors_used", 0) > 0:
                    row["drift_metrics"] = {
                        "status": "knn_computed",
                        "l2_to_medoid": sat_knn.get("l2_to_medoid"),
                        "knn_mean_l2_to_canon": sat_knn.get("knn_mean_l2_to_canon"),
                        "contrast_delta": sat_knn.get("contrast_delta"),
                        "vectors_used": sat_knn.get("vectors_used"),
                    }
                elif (
                    spec["corpus_type"] == "apocrypha"
                    and args.knn_drift_json.is_file()
                ):
                    knn_doc = json.loads(args.knn_drift_json.read_text(encoding="utf-8"))
                    if knn_doc.get("satellite", {}).get("row_count", 0) > 0:
                        row["drift_metrics"] = {
                            "status": "knn_computed",
                            "l2_to_medoid": knn_doc.get("satellite", {}).get("l2_to_medoid"),
                            "knn_mean_l2_to_canon": knn_doc.get("satellite", {}).get(
                                "knn_mean_l2_to_canon"
                            ),
                            "contrast_delta": knn_doc.get("contrast", {}).get(
                                "satellite_mean_minus_canon_mean"
                            ),
                        }
                    else:
                        row["drift_metrics"] = {
                            "status": "stub_pending_knn",
                            "note": "Run build_logos_satellite_knn_drift_pack_v1.py after lane ingest.",
                        }
                else:
                    row["drift_metrics"] = {
                        "status": "stub_pending_knn",
                        "note": "Run build_logos_dss_satellite_lane_v1.py + build_logos_satellite_knn_drift_pack_v1.py.",
                    }
        if spec.get("enriched_jsonl"):
            ep = ROOT / spec["enriched_jsonl"]
            row["enriched_jsonl"] = _rel(ep)
            row["enriched_jsonl_present"] = ep.is_file()
        if spec.get("manifest_ref"):
            mp = ROOT / spec["manifest_ref"]
            row["dss_manifest"] = _rel(mp)
            row["dss_manifest_present"] = mp.is_file()
            if mp.is_file():
                man = json.loads(mp.read_text(encoding="utf-8"))
                row["dss_enriched_row_count"] = man.get("row_count")
        if spec.get("lane_manifest_ref"):
            lp = ROOT / spec["lane_manifest_ref"]
            row["dss_lane_manifest"] = _rel(lp)
            row["dss_lane_manifest_present"] = lp.is_file()
            if lp.is_file():
                lane_man = json.loads(lp.read_text(encoding="utf-8"))
                row["dss_lane_row_count"] = lane_man.get("row_count")
        if spec.get("slot_mapping_ref"):
            sp = ROOT / spec["slot_mapping_ref"]
            row["dss_slot_mapping"] = _rel(sp)
            row["dss_slot_mapping_present"] = sp.is_file()
            if sp.is_file():
                slot_doc = json.loads(sp.read_text(encoding="utf-8"))
                sk = slot_doc.get("kpi") or {}
                row["dss_slot_mapped_count"] = sk.get("mapped_slot_count")
                row["dss_slot_coverage_rate"] = sk.get("slot_coverage_rate")
                row["dss_slot_mean_confidence_boost"] = sk.get("mean_confidence_boost")
        if spec.get("draft_ref"):
            p = ROOT / spec["draft_ref"]
            row["cross_ref_draft"] = _rel(p)
            row["cross_ref_present"] = p.is_file()
            if p.is_file():
                draft = json.loads(p.read_text(encoding="utf-8"))
                row["cross_ref_entry_count"] = len(draft.get("entries") or [])
        satellites.append(row)

    drift_metrics_ref: dict[str, Any] | None = None
    if args.drift_metrics_json.is_file():
        drift_metrics_ref = json.loads(args.drift_metrics_json.read_text(encoding="utf-8"))

    doc = {
        "schema": "logos_satellite_orbit_drift_v1",
        "version": "1.0.0",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "source_track": "B_ext",
        "canonical_anchor": {
            "corpus_manifest": _rel(args.corpus_manifest) if args.corpus_manifest.is_file() else None,
            "rows_emitted": (
                json.loads(args.corpus_manifest.read_text(encoding="utf-8")).get("counts", {}).get(
                    "rows_emitted"
                )
                if args.corpus_manifest.is_file()
                else None
            ),
            "global_medoid_verse_id": medoid_id,
            "complete_gap_nt_mt_only": coverage_gap,
            "constitution_ref": "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md §4 Multi-Corpus",
        },
        "satellites": satellites,
        "canonical_drift_metrics": drift_metrics_ref,
        "satellite_knn_drift": (
            json.loads(args.knn_drift_json.read_text(encoding="utf-8"))
            if args.knn_drift_json.is_file()
            else None
        ),
        "satellite_knn_drift_pack": knn_pack,
        "track_wall": {
            "a_track_auto_promotion": False,
            "ready_for_external_send": False,
            "default_cli_guard": "canonical_only unless --include-satellites",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output} medoid={medoid_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
