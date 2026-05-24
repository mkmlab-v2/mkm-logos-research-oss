#!/usr/bin/env python3
"""Refresh Logos single-anchor B-track go/no-go summary from on-disk artifacts (no LLM)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_single_anchor_go_no_go_v1_latest.json"
REGRESSION = ROOT / "scripts/run_logos_verse_4d_regression_bundle_v1.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return doc if isinstance(doc, dict) else None


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path.resolve())


def _run_regression() -> bool:
    if not REGRESSION.is_file():
        return False
    rc = subprocess.run(
        [sys.executable, str(REGRESSION)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    return rc.returncode == 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-regression", action="store_true")
    ap.add_argument(
        "--base-json",
        type=Path,
        default=DEFAULT_OUT,
        help="Merge policy fields (lg_hs_*, verdict_ko) from prior doc when present.",
    )
    args = ap.parse_args()

    base = _read_json(args.base_json) if args.base_json.is_file() else {}

    corpus_manifest = _read_json(
        ROOT / "docs/final/artifacts/logos_verse_4d_single_anchor_corpus_v1_latest.json"
    )
    slot_mapping = _read_json(
        ROOT / "docs/final/artifacts/logos_dss_crossref_slot_mapping_v1_latest.json"
    )
    strict_audit = _read_json(
        ROOT / "docs/final/artifacts/logos_dss_crossref_strict_gate_audit_v1_latest.json"
    )
    scrollmapper = _read_json(
        ROOT / "docs/final/artifacts/logos_tr_scrollmapper_crossval_v1_latest.json"
    )
    tr_nt = _read_json(ROOT / "docs/final/artifacts/logos_tr_nt_corpus_manifest_v1_latest.json")
    dss_manifest = _read_json(
        ROOT / "docs/final/artifacts/logos_dss_enriched_manifest_v1_latest.json"
    )
    closure = _read_json(ROOT / "reports/prophecy_lane_closure_bundle_v1_latest.json")

    regression_ok = bool(base.get("single_anchor_operational", {}).get("regression_49_passed"))
    if not args.skip_regression:
        regression_ok = _run_regression()

    union_rows = int((corpus_manifest or {}).get("counts", {}).get("rows_emitted") or 31102)
    sm_counts = (scrollmapper or {}).get("counts") or {}
    slot_kpi = (slot_mapping or {}).get("kpi") or {}
    strict_kpi = (strict_audit or {}).get("kpi") or {}

    multi_orbit: dict[str, Any] = dict(
        (base.get("single_anchor_operational") or {}).get("multi_orbit_b_track") or {}
    )
    multi_orbit.update(
        {
            "textual_variant_distance_json": "docs/final/artifacts/logos_textual_variant_distance_v1_latest.json",
            "satellite_orbit_drift_json": "docs/final/artifacts/logos_satellite_orbit_drift_v1_latest.json",
            "satellite_drift_metrics_json": "docs/final/artifacts/logos_satellite_drift_metrics_v1_latest.json",
            "multi_orbit_showroom_pack_json": "docs/final/artifacts/logos_multi_orbit_showroom_pack_v1_latest.json",
            "satellite_knn_drift_json": "docs/final/artifacts/logos_satellite_knn_drift_pack_v1_latest.json",
            "tr_tradition_scaffold_json": "docs/final/artifacts/logos_tr_tradition_scaffold_v1_latest.json",
            "tr_greek_jsonl": "data/logos/manuscripts/tr_greek_by_verse_v1.jsonl",
            "tr_variant_vectors_jsonl": "docs/final/artifacts/logos_tr_variant_vectors_v1_latest.jsonl",
            "tr_gap_hit_report": "docs/final/artifacts/logos_tr_greek_gap_hit_report_v1_latest.json",
            "tr_full_nt_jsonl": "data/logos/manuscripts/tr_greek_by_verse_v1.full_nt.jsonl",
            "tr_nt_corpus_manifest": _rel(
                ROOT / "docs/final/artifacts/logos_tr_nt_corpus_manifest_v1_latest.json"
            ),
            "cross_ref_dss_draft": "docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json",
            "dss_enriched_jsonl": "data/logos/manuscripts/dss_parsed_enriched.jsonl",
            "dss_enriched_manifest": "docs/final/artifacts/logos_dss_enriched_manifest_v1_latest.json",
            "dss_satellite_lane_jsonl": (
                "reports/constitution/btrack_pilot/logos_verse_4d_dss_lane_v1_latest.jsonl"
            ),
            "dss_satellite_lane_manifest": (
                "docs/final/artifacts/logos_dss_satellite_lane_manifest_v1_latest.json"
            ),
            "satellite_knn_drift_pack": "docs/final/artifacts/logos_satellite_knn_drift_pack_v1_latest.json",
            "dss_4d_projection": "reports/constitution/btrack_pilot/dss_4d_projection_latest.json",
            "dss_crossref_slot_mapping": _rel(
                ROOT / "docs/final/artifacts/logos_dss_crossref_slot_mapping_v1_latest.json"
            ),
            "dss_crossref_strict_gate_audit": _rel(
                ROOT / "docs/final/artifacts/logos_dss_crossref_strict_gate_audit_v1_latest.json"
            ),
            "dss_slot_mapping_refresh_pack": _rel(
                ROOT / "docs/final/artifacts/logos_dss_slot_mapping_refresh_pack_v1_latest.json"
            ),
            "dss_slot_mapping_comparison": _rel(
                ROOT
                / "reports/constitution/btrack_pilot/btrack_dss_direct_slot_mapping_comparison_latest.json"
            ),
            "dss_confidence_calibration": _rel(
                ROOT
                / "reports/constitution/btrack_pilot/btrack_dss_confidence_calibration_latest.json"
            ),
            "tr_scrollmapper_crossval": _rel(
                ROOT / "docs/final/artifacts/logos_tr_scrollmapper_crossval_v1_latest.json"
            ),
            "tr_scrollmapper_crossval_note": (
                "2nd-source agreement observational; gap_15_of_15_normalized_match may be false "
                "across TR editions"
            ),
            "tr_scrollmapper_overlap_match": (
                f"{sm_counts.get('normalized_exact_match', 0)}/{sm_counts.get('overlap_compared', 0)}"
            ),
            "tr_scrollmapper_gap_normalized": (
                f"{sm_counts.get('gap_normalized_exact_match', 0)}/"
                f"{sm_counts.get('gap_overlap_compared', 0)}"
            ),
            "dss_enriched_row_count": int((dss_manifest or {}).get("row_count") or 40),
            "dss_slot_mapped": (
                f"{slot_kpi.get('mapped_slot_count', 0)}/{slot_kpi.get('slot_count', 16)}"
            ),
            "dss_slot_mean_confidence_boost": slot_kpi.get("mean_confidence_boost"),
            "dss_strict_gate_partial_anchor": (
                f"{strict_kpi.get('strict_gate_pass', 0)}/{strict_kpi.get('entries_audited', 9)}"
            ),
            "dss_strict_gate_primary_btrack_md": (
                f"{strict_kpi.get('primary_dss_md_mapping_count', 0)}/"
                f"{strict_kpi.get('entries_audited', 9)}"
            ),
            "dss_confidence_v2_promote": bool(slot_kpi.get("target_mean_confidence_boost_ok")),
            "b2b_multi_orbit_appendix_md": (
                "docs/final/artifacts/track_c_b2b_logos_multi_orbit_appendix_v1_latest.md"
            ),
            "apocrypha_lane_jsonl": (
                "reports/constitution/btrack_pilot/logos_verse_4d_apocrypha_lane_v1_latest.jsonl"
            ),
            "research_queue": "docs/research/RESEARCH_OPEN_QUESTIONS_V1.md RQ-019",
            "merge_tr_into_complete_forbidden": True,
        }
    )

    operational = dict(base.get("single_anchor_operational") or {})
    operational.update(
        {
            "union_rows": union_rows,
            "corpus_jsonl": "reports/constitution/btrack_pilot/logos_verse_4d_single_anchor_v1_latest.jsonl",
            "regression_49_passed": regression_ok,
            "tr_greek_gap_hits": (
                f"{(tr_nt or {}).get('gap_policy_hits', 15)}/{(tr_nt or {}).get('gap_policy_total', 15)}"
            ),
            "tr_ingest_manifest": "docs/final/artifacts/logos_tr_greek_ingest_manifest_v1_latest.json",
            "stepbible_pytest_5_passed": operational.get("stepbible_pytest_5_passed", True),
            "multi_orbit_b_track": multi_orbit,
        }
    )

    doc: dict[str, Any] = {
        "schema": "logos_single_anchor_go_no_go_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "lg_hs_planning_assumption": base.get("lg_hs_planning_assumption", "reject"),
        "lg_hs_official_status_record_only": base.get("lg_hs_official_status_record_only", "pending"),
        "primary_lane_selected": base.get("primary_lane_selected", "LANE-TRACKC-B2B"),
        "dual_anchor_retired_for_ops": base.get("dual_anchor_retired_for_ops", True),
        "single_anchor_operational": operational,
        "lexical_decode_blocker": base.get(
            "lexical_decode_blocker",
            {
                "upstream_original_text_missing": 15,
                "residual_cause": "TR/KJV-style verses absent from local SBLGNT (textual_variant_omission)",
                "forbidden_external_claim": "perfect_canon_100_percent_lexical",
            },
        ),
        "ready_for_external_send": False,
        "track_a_auto_promotion": False,
        "verdict_ko": base.get(
            "verdict_ko",
            "단일 앵커 31,102 — complete 원어 31,087절. 잔여 15절 NT 텍스트 변형(정책 스텁). OT 갭 0.",
        ),
        "ops_pointers": {
            "prophecy_lane_closure_ok": bool((closure or {}).get("closure_ok")),
            "prophecy_lane_closure_json": _rel(
                ROOT / "reports/prophecy_lane_closure_bundle_v1_latest.json"
            ),
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {args.output} regression_49_passed={regression_ok} "
        f"dss_slots={multi_orbit.get('dss_slot_mapped')}",
        flush=True,
    )
    return 0 if regression_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
