#!/usr/bin/env python3
"""ENTRY_13 Ps.5.8-9 shadow deep-research supplement (NOT ENTRY_16) [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SHADOW = ROOT / "reports/shadow_4q_ps5_witness_registry_v1_latest.json"
WMAP = ROOT / "reports/dss_4q_ps5_line_witness_map_v1_latest.json"
VA_PKT = ROOT / "reports/entry_13_ps5_2_verified_anchor_evidence_packet_v1_latest.json"
INTAKE = ROOT / "data/logos/manuscripts/evidence_intake/entry_12_13_external_witness_v1.json"
OUT_JSON = ROOT / "reports/deep_research_entry_13_ps5_8_9_shadow_supplement_v1_latest.json"
OUT_MD = ROOT / "reports/deep_research_entry_13_ps5_8_9_shadow_supplement_v1_latest.md"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    shadow = _load(SHADOW)
    wmap = _load(WMAP)
    va = _load(VA_PKT)
    intake = _load(INTAKE)
    e13_intake = next(
        (r for r in intake.get("witness_promotions") or [] if r.get("entry_id") == "ENTRY_13"),
        {},
    )
    commander_row = next(
        (r for r in shadow.get("rows") or [] if r.get("commander_promoted")),
        {},
    )

    verified_facts = [
        {
            "id": "entry_mapping",
            "claim": "Ps.5.8-9 DSS shadow research attaches to ENTRY_13 (bench Ps.5.2), not ENTRY_16.",
            "ssot": "docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json ENTRY_13",
        },
        {
            "id": "shadow_commander_row",
            "claim": "4Q98b frg.1 line 1 is commander_verified_shadow_witness for Ps.5.8-9.",
            "witness_id": commander_row.get("witness_id"),
            "scroll": commander_row.get("scroll"),
            "ssot": "reports/shadow_4q_ps5_witness_registry_v1_latest.json",
        },
        {
            "id": "verified_anchor_gap",
            "claim": "MT Ps.5.2 v.2 direct line verified_anchor is not achieved.",
            "ssot": "reports/entry_13_ps5_2_verified_anchor_evidence_packet_v1_latest.json",
            "verified_anchor_achieved": va.get("verified_anchor_achieved"),
        },
        {
            "id": "11q5_missing_ps5",
            "claim": "11Q5 (Great Psalms Scroll) does not preserve Psalms 1–~89; no Ps.5 physical anchor on 11Q5.",
            "status": "missing_anchor",
            "ssot": "CROSS_REF ENTRY_12/13 prior_bench=11Q5(retired)",
        },
        {
            "id": "qd_4q98b",
            "claim": "Public QD transcription exists for 4Q98b (2025-03-11).",
            "url": e13_intake.get("evidence_url")
            or "https://lexicon.qumran-digital.org/transcriptions/4Q98b/2025-03-11/index.html",
        },
    ]

    hypotheses = [
        {
            "id": "4q83_ps5_9_13",
            "claim": "4Q83 (4QPs_a) Fragment 1 may preserve Ps 5:9–13 per DJD XVI / Study Edition tradents.",
            "tier": "[HYPO]",
            "mapping_status": "provisional_lexical_anchor",
            "note": "Requires DJD XVI plate/page cite before promotion; do not merge to CROSS_REF.",
        },
        {
            "id": "4q98b_plene_orthography",
            "claim": "4Q98b shows plene 2sg suffix (כה-) on shadow lines vs MT defective forms.",
            "tier": "[HYPO]",
            "source": "external_deep_research_intel",
        },
        {
            "id": "verse_numbering_bridge",
            "claim": "QD Hebrew numbering Ps 5:8–13 aligns with MT Ps 5:9–10 in English versification.",
            "tier": "[HYPO]",
        },
    ]

    missing_anchors = [
        {
            "source_id": "11Q5",
            "status": "missing_anchor",
            "gap": "No Ps.5 segment on 11Q5 scroll structure (starts ~Ps 90+).",
        },
        {
            "source_id": "MT_Ps.5.2_v2",
            "status": "missing_anchor",
            "gap": "No DSS line maps to MT Ps.5.2 opening (אמר/האזינה…) with contiguous substring.",
            "best_contiguous_substring_len": (va.get("witness_candidate_scan") or {}).get(
                "best_contiguous_substring_len"
            ),
        },
    ]

    shadow_data = [
        {
            "id": "4q174_4q177_catena",
            "dispute": "Ps 5 citations in 4Q174 Florilegium vs 4Q177 Catena — scroll height mismatch blocks single-scroll synthesis.",
            "integrity_risk": "Do not merge pesher catena rows into ENTRY_13 shadow rail.",
        },
        {
            "id": "romans_3_13_lxx_backflow",
            "dispute": "Patristic LXX/Rom 3:13 catena may harmonize Greek Psalter; isolate from Hebrew DSS witness path.",
            "integrity_risk": "shadow_data_only",
        },
    ]

    manuscripts = [
        {
            "siglum": "4Q98b",
            "scroll": "4Q98b",
            "role": "commander_verified_shadow_witness",
            "textual_range_hypothesis": "Ps 5:8–13; 6:1 (QD numbering)",
            "fragment": "frg.1",
            "lines": "1–6",
            "primary_refs": [
                "Ulrich et al., DJD XVI (4QPss)",
                "Qumran-Digital 4Q98b 2025-03-11",
            ],
            "pam_plate_note": "PAM/IAA plate IDs are not DJD plate numbers — verify before citing as DJD.",
        },
        {
            "siglum": "4Q83",
            "scroll": "4Q83",
            "role": "provisional_supplemental",
            "textual_range_hypothesis": "Ps 5:9–13 (literature tradents; not commander-promoted)",
            "mapping_status": "provisional_lexical_anchor",
            "primary_refs": ["DJD XVI (4QPs_a) — page cite required"],
        },
    ]

    doc = {
        "schema": "entry_13_ps5_shadow_deep_research_supplement_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "send_gate": "HOLD",
        "writes_canon": False,
        "cross_ref_entry_id": "ENTRY_13",
        "canonical_ref": "Ps.5.2",
        "shadow_verse_anchor": "Ps.5.8-9",
        "not_entry_16": True,
        "verified_anchor_achieved": False,
        "mt_ps_5_2_crosswalk_gap": True,
        "commander_shadow": {
            "witness_id": commander_row.get("witness_id"),
            "scroll": commander_row.get("scroll"),
            "line": commander_row.get("line"),
            "text_preview": next(
                (
                    w.get("text_preview")
                    for w in wmap.get("witnesses") or []
                    if w.get("witness_id") == commander_row.get("witness_id")
                ),
                None,
            ),
        },
        "verified_facts": verified_facts,
        "hypotheses": hypotheses,
        "missing_anchors": missing_anchors,
        "shadow_data": shadow_data,
        "manuscripts": manuscripts,
        "upstream_artifacts": [
            "reports/shadow_4q_ps5_witness_registry_v1_latest.json",
            "reports/dss_4q_ps5_line_witness_map_v1_latest.json",
            "reports/entry_13_ps5_2_verified_anchor_evidence_packet_v1_latest.json",
            "data/logos/manuscripts/evidence_intake/entry_12_13_external_witness_v1.json",
        ],
        "reproduce": "py scripts/build_entry_13_ps5_8_9_deep_research_supplement_v1.py",
    }
    return doc


def _md(doc: dict[str, Any]) -> str:
    lines = [
        "# [TRACK B / HYPO] ENTRY_13 — Ps.5.8-9 shadow deep-research supplement",
        "",
        f"- Generated: {doc['generated_at_utc']}",
        f"- **ENTRY_13** bench `Ps.5.2` · shadow `Ps.5.8-9` · **NOT ENTRY_16**",
        f"- `verified_anchor_achieved`: **{doc['verified_anchor_achieved']}** · `send_gate`: **{doc['send_gate']}**",
        "",
        "## Commander shadow (fact)",
        "",
        f"- Scroll **{doc['commander_shadow'].get('scroll')}** frg.1 line {doc['commander_shadow'].get('line')}",
        f"- witness_id: `{doc['commander_shadow'].get('witness_id')}`",
        "",
        "## Verified facts",
        "",
    ]
    for f in doc.get("verified_facts") or []:
        lines.append(f"- **{f.get('id')}**: {f.get('claim')}")
    lines.extend(["", "## Hypotheses [HYPO]", ""])
    for h in doc.get("hypotheses") or []:
        lines.append(f"- **{h.get('id')}**: {h.get('claim')}")
    lines.extend(["", "## Missing anchors", ""])
    for m in doc.get("missing_anchors") or []:
        lines.append(f"- `{m.get('source_id')}` → **{m.get('status')}**: {m.get('gap')}")
    lines.extend(["", "## Shadow data (isolated)", ""])
    for s in doc.get("shadow_data") or []:
        lines.append(f"- **{s.get('id')}**: {s.get('dispute')}")
    lines.extend(
        [
            "",
            "Reproduce: `py scripts/build_entry_13_ps5_8_9_deep_research_supplement_v1.py`",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json-out", type=Path, default=OUT_JSON)
    ap.add_argument("--md-out", type=Path, default=OUT_MD)
    args = ap.parse_args()
    doc = build()
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.md_out.write_text(_md(doc), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "entry_id": doc["cross_ref_entry_id"],
                "verified_anchor_achieved": doc["verified_anchor_achieved"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
