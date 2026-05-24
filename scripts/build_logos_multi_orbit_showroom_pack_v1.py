#!/usr/bin/env python3
"""Assemble B-track Multi-Orbit internal showroom pack (no canon row merge)."""

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

DEFAULT_VARIANT = ROOT / "docs/final/artifacts/logos_textual_variant_distance_v1_latest.json"
DEFAULT_ORBIT = ROOT / "docs/final/artifacts/logos_satellite_orbit_drift_v1_latest.json"
DEFAULT_METRICS = ROOT / "docs/final/artifacts/logos_satellite_drift_metrics_v1_latest.json"
DEFAULT_CLASSIFY = ROOT / "docs/final/artifacts/logos_gap_mt_only_residual_classify_v1_latest.json"
DEFAULT_KNN = ROOT / "docs/final/artifacts/logos_satellite_knn_drift_v1_latest.json"
DEFAULT_TR = ROOT / "docs/final/artifacts/logos_tr_tradition_scaffold_v1_latest.json"
DEFAULT_TR_NT = ROOT / "docs/final/artifacts/logos_tr_nt_corpus_manifest_v1_latest.json"
DEFAULT_DSS_SLOTS = ROOT / "docs/final/artifacts/logos_dss_crossref_slot_mapping_v1_latest.json"
DEFAULT_DSS_STRICT_AUDIT = ROOT / "docs/final/artifacts/logos_dss_crossref_strict_gate_audit_v1_latest.json"
DEFAULT_DSS_REFRESH_PACK = ROOT / "docs/final/artifacts/logos_dss_slot_mapping_refresh_pack_v1_latest.json"
DEFAULT_KNN_PACK = ROOT / "docs/final/artifacts/logos_satellite_knn_drift_pack_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_multi_orbit_showroom_pack_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--variant-json", type=Path, default=DEFAULT_VARIANT)
    ap.add_argument("--orbit-json", type=Path, default=DEFAULT_ORBIT)
    ap.add_argument("--metrics-json", type=Path, default=DEFAULT_METRICS)
    ap.add_argument("--classify-json", type=Path, default=DEFAULT_CLASSIFY)
    ap.add_argument("--knn-json", type=Path, default=DEFAULT_KNN)
    ap.add_argument("--tr-json", type=Path, default=DEFAULT_TR)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    variant = _load(args.variant_json)
    orbit = _load(args.orbit_json)
    metrics = _load(args.metrics_json)
    classify = _load(args.classify_json)
    knn = _load(args.knn_json)
    tr = _load(args.tr_json)
    tr_nt = _load(DEFAULT_TR_NT)
    dss_slots = _load(DEFAULT_DSS_SLOTS)
    knn_pack = _load(DEFAULT_KNN_PACK)

    if variant is None:
        print(f"missing variant: {args.variant_json}", file=sys.stderr)
        return 2

    agg = variant.get("aggregate") or {}
    medoid = (orbit or {}).get("canonical_anchor", {}).get("global_medoid_verse_id")
    if not medoid and metrics:
        medoid = metrics.get("medoid_verse_id")

    doc = {
        "schema": "logos_multi_orbit_showroom_pack_v1",
        "version": "1.0.0",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "source_track": "B_ext",
        "headline": (
            "31,102 MT canon union with 15 NT textual-variant MT-only stubs isolated; "
            "satellite corpora (DSS/apocrypha) remain separate orbits."
        ),
        "summary": {
            "complete_gap_nt": agg.get("entry_count"),
            "distance_status_counts": agg.get("distance_status_counts"),
            "global_medoid_verse_id": medoid,
            "canon_l2_to_medoid_mean": (metrics or {})
            .get("canon_population", {})
            .get("mean"),
            "gap_l2_to_medoid_mean": (metrics or {})
            .get("mt_only_gap_population", {})
            .get("mean"),
            "residual_taxonomy": (classify or {}).get("residual_taxonomy_counts"),
            "apocrypha_satellite_rows": (knn or {}).get("satellite", {}).get("row_count"),
            "apocrypha_l2_to_medoid_mean": (knn or {})
            .get("satellite", {})
            .get("l2_to_medoid", {})
            .get("mean"),
            "tr_scaffold_verse_count": (tr or {}).get("verse_count"),
            "tr_full_nt_row_count": (tr_nt or {}).get("row_count"),
            "tr_full_nt_gap_hits": (tr_nt or {}).get("gap_policy_hits"),
            "dss_slot_mapped": (dss_slots or {}).get("kpi", {}).get("mapped_slot_count"),
            "dss_slot_coverage_rate": (dss_slots or {}).get("kpi", {}).get("slot_coverage_rate"),
            "dss_slot_mean_confidence_boost": (dss_slots or {}).get("kpi", {}).get(
                "mean_confidence_boost"
            ),
            "dss_satellite_vectors_used": (knn_pack or {})
            .get("satellites", {})
            .get("dss", {})
            .get("vectors_used"),
        },
        "artifact_refs": {
            "textual_variant_distance": str(args.variant_json.relative_to(ROOT)).replace("\\", "/")
            if args.variant_json.is_file()
            else None,
            "satellite_orbit_drift": str(args.orbit_json.relative_to(ROOT)).replace("\\", "/")
            if args.orbit_json.is_file()
            else None,
            "satellite_drift_metrics": str(args.metrics_json.relative_to(ROOT)).replace("\\", "/")
            if args.metrics_json.is_file()
            else None,
            "residual_classify": str(args.classify_json.relative_to(ROOT)).replace("\\", "/")
            if args.classify_json.is_file()
            else None,
            "satellite_knn_drift": str(args.knn_json.relative_to(ROOT)).replace("\\", "/")
            if args.knn_json.is_file()
            else None,
            "tr_tradition_scaffold": str(args.tr_json.relative_to(ROOT)).replace("\\", "/")
            if args.tr_json.is_file()
            else None,
            "dss_crossref_slot_mapping": str(DEFAULT_DSS_SLOTS.relative_to(ROOT)).replace("\\", "/")
            if DEFAULT_DSS_SLOTS.is_file()
            else None,
            "dss_crossref_strict_gate_audit": str(DEFAULT_DSS_STRICT_AUDIT.relative_to(ROOT)).replace("\\", "/")
            if DEFAULT_DSS_STRICT_AUDIT.is_file()
            else None,
            "dss_slot_mapping_refresh_pack": str(DEFAULT_DSS_REFRESH_PACK.relative_to(ROOT)).replace("\\", "/")
            if DEFAULT_DSS_REFRESH_PACK.is_file()
            else None,
            "satellite_knn_drift_pack": str(DEFAULT_KNN_PACK.relative_to(ROOT)).replace("\\", "/")
            if DEFAULT_KNN_PACK.is_file()
            else None,
        },
        "track_wall": {
            "merge_into_complete_jsonl": False,
            "a_track_auto_promotion": False,
            "ready_for_external_send": False,
            "forbidden_claim": "primary_bhs_sblgnt_decode_for_all_31102",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
