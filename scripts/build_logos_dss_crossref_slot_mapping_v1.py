#!/usr/bin/env python3
"""Build DSS × CROSS_REF 16-slot mapping for Logos Multi-Orbit (B-track, NON_GATING)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MAPPER = ROOT / "scripts/map_dss_rows_to_16_anchor_slots.py"
DEFAULT_DSS = ROOT / "data/logos/manuscripts/dss_parsed_enriched.jsonl"
DEFAULT_CROSS = ROOT / "docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json"
DEFAULT_REPORT = ROOT / "reports/constitution/btrack_pilot/btrack_dss_direct_slot_mapping_latest.json"
DEFAULT_ARTIFACT = ROOT / "docs/final/artifacts/logos_dss_crossref_slot_mapping_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    resolved = path.resolve()
    root = ROOT.resolve()
    if resolved == root or root in resolved.parents:
        return str(resolved.relative_to(root)).replace("\\", "/")
    return str(resolved.as_posix())


def _envelope(report: dict[str, Any]) -> dict[str, Any]:
    kpi = report.get("kpi") or {}
    return {
        "schema": "logos_dss_crossref_slot_mapping_v1",
        "version": "1.0.0",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "source_track": "B_ext",
        "upstream_schema": report.get("schema"),
        "cross_ref_draft": _rel(DEFAULT_CROSS),
        "inputs": {
            "dss_enriched_jsonl": _rel(DEFAULT_DSS),
            "mapper_script": _rel(MAPPER),
            "confidence_mode": (report.get("inputs") or {}).get("confidence_mode"),
        },
        "kpi": kpi,
        "mappings": report.get("mappings") or [],
        "track_wall": {
            "merge_into_canon_complete_jsonl": False,
            "a_track_auto_promotion": False,
            "ready_for_external_send": False,
            "non_gating": True,
            "note": "Token overlap heuristic vs CROSS_REF ENTRY text; not theological or market truth.",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dss-enriched", type=Path, default=DEFAULT_DSS)
    ap.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--artifact-out", type=Path, default=DEFAULT_ARTIFACT)
    ap.add_argument("--confidence-mode", choices=("v1", "v2"), default="v2")
    args = ap.parse_args()

    if not args.dss_enriched.is_file():
        print(f"missing {args.dss_enriched}", file=sys.stderr)
        return 2
    if not DEFAULT_CROSS.is_file():
        print(f"missing {DEFAULT_CROSS}", file=sys.stderr)
        return 2

    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    rc = subprocess.run(
        [
            sys.executable,
            str(MAPPER),
            "--dss-enriched",
            str(args.dss_enriched),
            "--out",
            str(args.report_out),
            "--confidence-mode",
            args.confidence_mode,
        ],
        cwd=str(ROOT),
    )
    if rc.returncode != 0:
        return rc.returncode

    report = json.loads(args.report_out.read_text(encoding="utf-8"))
    artifact = _envelope(report)
    args.artifact_out.parent.mkdir(parents=True, exist_ok=True)
    args.artifact_out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    kpi = artifact.get("kpi") or {}
    print(
        f"wrote {args.artifact_out} "
        f"mapped={kpi.get('mapped_slot_count')}/16 "
        f"mean_conf={kpi.get('mean_confidence_boost')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
