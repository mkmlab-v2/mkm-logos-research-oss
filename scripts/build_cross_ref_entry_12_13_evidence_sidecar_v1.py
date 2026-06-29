#!/usr/bin/env python3
"""CROSS_REF ENTRY_12/13 evidence sidecar (shadow; no CROSS_REF draft mutation) [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CROSS_REF = ROOT / "docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json"
MT_ONLY = ROOT / "reports/cross_ref_entry_12_mt_only_sidecar_v1_latest.json"
BENCH_RELABEL = ROOT / "reports/cross_ref_entry_12_13_bench_relabel_sidecar_v1_latest.json"
MAP_4Q = ROOT / "reports/dss_4q_ps5_line_witness_map_v1_latest.json"
P5_GATE = ROOT / "docs/final/artifacts/p5_manuscript_integrity_gate_v1_latest.json"
SCAN = ROOT / "reports/dss_line_witness_verification_scan_v1_latest.json"
INTAKE = ROOT / "data/logos/manuscripts/evidence_intake/entry_12_13_external_witness_v1.json"
OUT_DEFAULT = ROOT / "reports/cross_ref_entry_12_13_evidence_sidecar_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def _entry_from_p5(
    entry_id: str,
    cross: dict[str, Any],
    bench: dict[str, Any],
    mt_only: dict[str, Any],
    map_4q: dict[str, Any],
    scan: dict[str, Any],
) -> dict[str, Any]:
    cross_by_id = {e.get("entry_id"): e for e in cross.get("entries") or [] if e.get("entry_id")}
    bench_by_id = {e.get("entry_id"): e for e in bench.get("entries") or [] if e.get("entry_id")}
    scan_by_id = {e.get("entry_id"): e for e in scan.get("entries") or []}
    cr = cross_by_id.get(entry_id) or {}
    br = bench_by_id.get(entry_id) or {}
    sc = scan_by_id.get(entry_id) or {}

    if entry_id == "ENTRY_12":
        rail = br.get("new_witness_rail") or mt_only.get("witness_rail") or "mt_only"
        status = "mt_only_no_qumran_witness"
        provisional = 0
        waiting = (
            "No Qumran Hebrew line witness for Ps.4.6 in local ETCBC; "
            "11Q5 bench hypothesis retired (scroll = Psalms 101+)."
        )
    else:
        rail = br.get("new_witness_rail") or "4Q83_4Q98b_shadow"
        verified = sum(
            1
            for w in map_4q.get("witnesses") or []
            if str(w.get("mapping_status", "")).startswith("commander_verified")
        )
        provisional = int((map_4q.get("summary") or {}).get("provisional_lexical_anchor_rows") or 0)
        if verified >= 1:
            status = "commander_verified_shadow_witness (4Q98b)"
            waiting = "Shadow rail promoted per commander intake; MT Ps.5.2 direct crosswalk still gap — Ps 5:8-9 anchor."
        else:
            status = "provisional_lexical_anchor (4Q shadow)"
            waiting = (
                "4Q83/4Q98b provisional lexical anchors only; "
                "DJD/Qumran-Digital col/line anchor required for verified_anchor."
            )

    return {
        "entry_id": entry_id,
        "canonical_ref": cr.get("canonical_ref") or br.get("canonical_ref") or map_4q.get("canon_verse_id"),
        "cross_ref_satellite_ref": cr.get("satellite_ref"),
        "prior_satellite": br.get("prior_satellite") or "11Q5",
        "bench_status": br.get("bench_status") or mt_only.get("eleven_q5_bench_status"),
        "witness_rail": rail,
        "current_anchor_status": status,
        "target_anchor_status": "verified_anchor",
        "p3_provisional_witness_count": provisional,
        "auto_scan_verified_count": sc.get("auto_verified_count"),
        "auto_scan_strong_candidate_count": sc.get("strong_candidate_count"),
        "promotion_eligible": int(sc.get("auto_verified_count") or 0) >= 1,
        "waiting_queue_reason": waiting,
        "required_evidence": [
            "primary_transcription_line_ref",
            "edition_citation",
            "col_line_or_fragment_sigla",
            "witness_id_crosswalk",
        ],
    }


def build() -> dict[str, Any]:
    cross = _load(CROSS_REF)
    mt_only = _load(MT_ONLY)
    bench = _load(BENCH_RELABEL)
    map_4q = _load(MAP_4Q)
    p5 = _load(P5_GATE)
    scan = _load(SCAN)
    intake = _load(INTAKE)

    entries = [
        _entry_from_p5("ENTRY_12", cross, bench, mt_only, map_4q, scan),
        _entry_from_p5("ENTRY_13", cross, bench, mt_only, map_4q, scan),
    ]
    intake_rows = intake.get("witness_promotions") or []
    manual_eligible = sum(1 for r in intake_rows if r.get("approve_promotion") is True)

    return {
        "schema": "cross_ref_entry_12_13_evidence_sidecar_v1",
        "version": "1.1.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "send_gate": "HOLD",
        "p5_manuscript_integrity_gate_ok": p5.get("gate_ok"),
        "track_wall": {
            "cross_ref_draft_mutation_forbidden": True,
            "logos_core_mutation_forbidden": True,
            "merge_into_canon_31k_41k": False,
        },
        "summary": {
            "entries": len(entries),
            "auto_promotion_eligible": sum(1 for e in entries if e.get("promotion_eligible")),
            "manual_intake_rows": len(intake_rows),
            "manual_promotion_eligible": manual_eligible,
            "entry_12_witness_rail": entries[0].get("witness_rail"),
            "entry_13_provisional_4q_rows": entries[1].get("p3_provisional_witness_count"),
        },
        "external_intake_path": str(INTAKE.relative_to(ROOT)).replace("\\", "/"),
        "intake_template": "data/logos/manuscripts/evidence_intake/entry_12_13_external_witness_v1.template.json",
        "entries": entries,
        "manual_intake": intake if intake else None,
        "reproduce": "py scripts/build_cross_ref_entry_12_13_evidence_sidecar_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "summary": doc["summary"], "out": str(args.out.relative_to(ROOT))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
