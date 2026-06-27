#!/usr/bin/env python3
"""Audit CROSS_REF partial-anchor strict gates vs DSS slot mapping quality (B-track)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CROSS = ROOT / "docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json"
DEFAULT_MAPPING = ROOT / "docs/final/artifacts/logos_dss_crossref_slot_mapping_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_dss_crossref_strict_gate_audit_v1_latest.json"

# Mirrors tests/test_cross_ref_dss_schema.py partial-anchor contract.
STRICT_PARTIAL_MARKERS: dict[str, str] = {
    "ENTRY_06": "status=partial_anchor_verified (column+line-range)",
    "ENTRY_07": "status=partial_anchor_verified (column-range)",
    "ENTRY_08": "status=partial_anchor_verified (sigla+plates)",
    "ENTRY_09": "status=partial_anchor_verified (frag+col+line-range)",
    "ENTRY_10": "status=partial_anchor_verified (plates+line)",
    "ENTRY_12": "status=mt_only_no_qumran_witness",
    "ENTRY_13": "status=commander_verified_shadow_witness",
    "ENTRY_14": "status=partial_anchor_verified (witness-set+plates+line)",
    "ENTRY_15": "status=partial_anchor_verified (witness-set+plates+chapter-range)",
}

META_DOC_HINTS = ("checklist", "closeout", "bundle_note", "cross_ref_citation")
PRIMARY_DSS_HINTS = ("btrack_dss_",)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    resolved = path.resolve()
    root = ROOT.resolve()
    if resolved == root or root in resolved.parents:
        return str(resolved.relative_to(root)).replace("\\", "/")
    return str(resolved.as_posix())


def _source_tier(source_doc: str) -> str:
    low = source_doc.lower().replace("\\", "/")
    if any(h in low for h in META_DOC_HINTS):
        return "operational_meta"
    if any(h in low for h in PRIMARY_DSS_HINTS):
        return "primary_dss_md"
    return "other"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cross-ref", type=Path, default=DEFAULT_CROSS)
    ap.add_argument("--slot-mapping", type=Path, default=DEFAULT_MAPPING)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--entry-ids",
        default=",".join(STRICT_PARTIAL_MARKERS.keys()),
        help="Comma-separated ENTRY_* ids to audit (default: partial-anchor set)",
    )
    args = ap.parse_args()

    if not args.cross_ref.is_file():
        print(f"missing {args.cross_ref}", file=sys.stderr)
        return 2
    if not args.slot_mapping.is_file():
        print(f"missing {args.slot_mapping}", file=sys.stderr)
        return 2

    cross = json.loads(args.cross_ref.read_text(encoding="utf-8"))
    mapping_doc = json.loads(args.slot_mapping.read_text(encoding="utf-8"))
    by_entry = {str(m.get("entry_id")): m for m in mapping_doc.get("mappings") or [] if m.get("entry_id")}

    entry_ids = [x.strip() for x in str(args.entry_ids).split(",") if x.strip()]
    rows: list[dict[str, Any]] = []
    cross_ref_pass = 0
    mapping_pass = 0
    primary_source_count = 0

    for eid in entry_ids:
        entry = next((e for e in cross.get("entries", []) if e.get("entry_id") == eid), None)
        marker = STRICT_PARTIAL_MARKERS.get(eid)
        sat = str((entry or {}).get("satellite_ref") or "")
        marker_ok = bool(marker and marker in sat) if marker else None
        if marker_ok:
            cross_ref_pass += 1

        mp = by_entry.get(eid) or {}
        if not mp.get("mapped"):
            # Fallback: mapper keys by state_id; cross-ref entry_id is authoritative for audit rows.
            sid = (entry or {}).get("state_candidate_id")
            if isinstance(sid, int):
                mp = next(
                    (m for m in mapping_doc.get("mappings") or [] if m.get("state_id") == sid),
                    mp,
                )
        mapped = bool(mp.get("mapped"))
        if mapped:
            mapping_pass += 1
        src = str(mp.get("dss_source_doc") or "")
        tier = _source_tier(src) if src else "unmapped"
        if tier == "primary_dss_md":
            primary_source_count += 1

        rows.append(
            {
                "entry_id": eid,
                "state_id": (entry or {}).get("state_candidate_id"),
                "canonical_ref": (entry or {}).get("canonical_ref"),
                "expected_partial_marker": marker,
                "cross_ref_marker_ok": marker_ok,
                "satellite_ref_excerpt": sat[:160] + ("…" if len(sat) > 160 else ""),
                "slot_mapped": mapped,
                "match_score": mp.get("match_score"),
                "dss_row_id": mp.get("dss_row_id"),
                "dss_source_doc": src.replace("\\", "/") if src else None,
                "dss_source_tier": tier,
                "confidence_boost": mp.get("confidence_boost"),
                "strict_gate_ok": bool(marker_ok) and mapped,
            }
        )

    n = len(entry_ids)
    doc = {
        "schema": "logos_dss_crossref_strict_gate_audit_v1",
        "version": "1.0.0",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "inputs": {
            "cross_ref_draft": _rel(args.cross_ref),
            "slot_mapping": _rel(args.slot_mapping),
            "entry_ids": entry_ids,
        },
        "kpi": {
            "entries_audited": n,
            "cross_ref_marker_pass": cross_ref_pass,
            "slot_mapping_pass": mapping_pass,
            "strict_gate_pass": sum(1 for r in rows if r.get("strict_gate_ok")),
            "primary_dss_md_mapping_count": primary_source_count,
            "cross_ref_marker_rate": round(cross_ref_pass / n, 6) if n else None,
            "primary_dss_md_rate": round(primary_source_count / mapping_pass, 6) if mapping_pass else None,
        },
        "gate": {
            "cross_ref_contract_ok": cross_ref_pass == n,
            "all_slots_mapped": mapping_pass == n,
            "note": (
                "strict_gate_ok requires CROSS_REF partial_anchor marker + slot row; "
                "dss_source_tier=operational_meta is flagged, not auto-fail."
            ),
        },
        "entries": rows,
        "track_wall": {
            "ready_for_external_send": False,
            "a_track_auto_promotion": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {args.output} strict={doc['kpi']['strict_gate_pass']}/{n} "
        f"primary_dss_md={primary_source_count}/{mapping_pass}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
