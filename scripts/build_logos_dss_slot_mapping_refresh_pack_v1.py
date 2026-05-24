#!/usr/bin/env python3
"""Full vs canonical-only DSS slot mapping refresh + comparison + calibration (Logos pack)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

FILTER = ROOT / "scripts/filter_dss_enriched_canonical_only.py"
MAPPER = ROOT / "scripts/map_dss_rows_to_16_anchor_slots.py"
COMPARE = ROOT / "scripts/report_dss_slot_mapping_comparison.py"
CALIB = ROOT / "scripts/ops/export_dss_confidence_calibration_log.py"
STRICT_AUDIT = ROOT / "scripts/build_logos_dss_crossref_strict_gate_audit_v1.py"

FULL_IN = ROOT / "data/logos/manuscripts/dss_parsed_enriched.jsonl"
CANON_IN = ROOT / "data/logos/manuscripts/dss_parsed_enriched_canonical_only.jsonl"
FULL_REPORT = ROOT / "reports/constitution/btrack_pilot/btrack_dss_direct_slot_mapping_latest.json"
CANON_REPORT = ROOT / "reports/constitution/btrack_pilot/btrack_dss_direct_slot_mapping_canonical_latest.json"
COMPARE_REPORT = ROOT / "reports/constitution/btrack_pilot/btrack_dss_direct_slot_mapping_comparison_latest.json"
CALIB_REPORT = ROOT / "reports/constitution/btrack_pilot/btrack_dss_confidence_calibration_latest.json"

DEFAULT_PACK = ROOT / "docs/final/artifacts/logos_dss_slot_mapping_refresh_pack_v1_latest.json"
DEFAULT_ARTIFACT_COMPARE = ROOT / "docs/final/artifacts/logos_dss_slot_mapping_comparison_v1_latest.json"
DEFAULT_ARTIFACT_CALIB = ROOT / "docs/final/artifacts/logos_dss_confidence_calibration_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    resolved = path.resolve()
    root = ROOT.resolve()
    if resolved == root or root in resolved.parents:
        return str(resolved.relative_to(root)).replace("\\", "/")
    return str(resolved.as_posix())


def _run(cmd: list[str]) -> int:
    print(" ".join(cmd), flush=True)
    return int(subprocess.run(cmd, cwd=str(ROOT)).returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--confidence-mode", choices=("v1", "v2"), default="v2")
    ap.add_argument("--skip-strict-audit", action="store_true")
    ap.add_argument("--output-pack", type=Path, default=DEFAULT_PACK)
    args = ap.parse_args()

    py = sys.executable
    steps: list[tuple[str, list[str]]] = [
        ("filter_canonical", [py, str(FILTER)]),
        (
            "map_full",
            [
                py,
                str(MAPPER),
                "--dss-enriched",
                str(FULL_IN),
                "--out",
                str(FULL_REPORT),
                "--confidence-mode",
                args.confidence_mode,
            ],
        ),
        (
            "map_canonical",
            [
                py,
                str(MAPPER),
                "--dss-enriched",
                str(CANON_IN),
                "--out",
                str(CANON_REPORT),
                "--confidence-mode",
                args.confidence_mode,
            ],
        ),
        ("compare", [py, str(COMPARE)]),
        ("calibration", [py, str(CALIB)]),
    ]

    for name, cmd in steps:
        rc = _run(cmd)
        if rc != 0:
            print(f"failed at {name}", file=sys.stderr)
            return rc

    # Mirror primary DSS mapping artifact (full) for Logos chain consumers.
    rc = _run(
        [
            py,
            str(ROOT / "scripts/build_logos_dss_crossref_slot_mapping_v1.py"),
            "--dss-enriched",
            str(FULL_IN),
        ]
    )
    if rc != 0:
        return rc

    if not args.skip_strict_audit:
        rc = _run(
            [
                py,
                str(STRICT_AUDIT),
                "--slot-mapping",
                str(ROOT / "docs/final/artifacts/logos_dss_crossref_slot_mapping_v1_latest.json"),
            ]
        )
        if rc != 0:
            print("failed at strict_gate_audit", file=sys.stderr)
            return rc

    compare = json.loads(COMPARE_REPORT.read_text(encoding="utf-8")) if COMPARE_REPORT.is_file() else {}
    calib = json.loads(CALIB_REPORT.read_text(encoding="utf-8")) if CALIB_REPORT.is_file() else {}
    filter_rep_path = ROOT / "reports/constitution/btrack_pilot/dss_canonical_filter_report_latest.json"
    filter_rep = json.loads(filter_rep_path.read_text(encoding="utf-8")) if filter_rep_path.is_file() else {}

    artifact_compare = {
        "schema": "logos_dss_slot_mapping_comparison_v1",
        "version": "1.0.0",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "upstream_schema": compare.get("schema"),
        "full_kpi": compare.get("full_kpi"),
        "canonical_kpi": compare.get("canonical_kpi"),
        "delta": compare.get("delta"),
        "track_wall": {"ready_for_external_send": False},
    }
    DEFAULT_ARTIFACT_COMPARE.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_ARTIFACT_COMPARE.write_text(
        json.dumps(artifact_compare, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    artifact_calib = {
        "schema": "logos_dss_confidence_calibration_v1",
        "version": "1.0.0",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "upstream_schema": calib.get("schema"),
        "confidence_mode": calib.get("confidence_mode"),
        "confidence_params": calib.get("confidence_params"),
        "full": calib.get("full"),
        "canonical_only": calib.get("canonical_only"),
        "decision": calib.get("decision"),
        "track_wall": {"ready_for_external_send": False},
    }
    DEFAULT_ARTIFACT_CALIB.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_ARTIFACT_CALIB.write_text(
        json.dumps(artifact_calib, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    strict_path = ROOT / "docs/final/artifacts/logos_dss_crossref_strict_gate_audit_v1_latest.json"
    strict_doc: dict[str, Any] | None = None
    if strict_path.is_file():
        strict_doc = json.loads(strict_path.read_text(encoding="utf-8"))

    pack = {
        "schema": "logos_dss_slot_mapping_refresh_pack_v1",
        "version": "1.0.0",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "confidence_mode": args.confidence_mode,
        "canonical_filter": filter_rep,
        "reports": {
            "full_mapping": _rel(FULL_REPORT),
            "canonical_mapping": _rel(CANON_REPORT),
            "comparison": _rel(COMPARE_REPORT),
            "calibration": _rel(CALIB_REPORT),
        },
        "artifacts": {
            "slot_mapping": "docs/final/artifacts/logos_dss_crossref_slot_mapping_v1_latest.json",
            "comparison": _rel(DEFAULT_ARTIFACT_COMPARE),
            "calibration": _rel(DEFAULT_ARTIFACT_CALIB),
            "strict_gate_audit": _rel(strict_path) if strict_doc else None,
        },
        "strict_gate_audit_kpi": (strict_doc or {}).get("kpi"),
        "calibration_decision": calib.get("decision"),
        "track_wall": {
            "ready_for_external_send": False,
            "merge_into_canon_forbidden": True,
        },
    }
    args.output_pack.parent.mkdir(parents=True, exist_ok=True)
    args.output_pack.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output_pack}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
