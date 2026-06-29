#!/usr/bin/env python3
"""ENTRY_13 MT Ps.5.2 verified_anchor evidence packet (shadow rail separate) [HYPO]."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANON = ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_v1_latest.jsonl"
MAP_4Q = ROOT / "reports/dss_4q_ps5_line_witness_map_v1_latest.json"
INTAKE = ROOT / "data/logos/manuscripts/evidence_intake/entry_12_13_external_witness_v1.json"
CROSS = ROOT / "docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json"
OUT_JSON = ROOT / "reports/entry_13_ps5_2_verified_anchor_evidence_packet_v1_latest.json"
OUT_MD = ROOT / "reports/entry_13_ps5_2_verified_anchor_evidence_packet_v1_latest.md"

MT_OPENING_TOKENS = ("אמר", "האזינ", "יהוה", "בינ", "הגיג")
QD_4Q98B_URL = "https://lexicon.qumran-digital.org/transcriptions/4Q98b/2025-03-11/index.html"
QD_VERSE_SCOPE = "Ps 5:8-13 (QD Hebrew numbering on 4Q98b frg.1)"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _canon_ps_5_2() -> dict[str, Any]:
    if not CANON.is_file():
        return {}
    for line in CANON.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if row.get("verse_id") == "Ps.5.2":
            span = row.get("text_span") or {}
            return {
                "verse_id": "Ps.5.2",
                "source_ref": row.get("source_ref"),
                "hebrew_text": span.get("original_script_text"),
                "gematria_hebrew": (row.get("gematria_v1") or {}).get("hebrew_value"),
            }
    return {}


def _normalize_hebrew(s: str) -> str:
    return re.sub(r"[\s/־]+", "", s or "")


def _opening_hit_count(text: str) -> int:
    norm = _normalize_hebrew(text)
    hits = 0
    for tok in MT_OPENING_TOKENS:
        if tok in norm:
            hits += 1
    return hits


def build() -> dict[str, Any]:
    wmap = _load(MAP_4Q)
    intake = _load(INTAKE)
    cross = _load(CROSS)
    e13_intake = next((r for r in intake.get("witness_promotions") or [] if r.get("entry_id") == "ENTRY_13"), {})
    e13_cross = next((e for e in cross.get("entries") or [] if e.get("entry_id") == "ENTRY_13"), {})
    canon = _canon_ps_5_2()

    candidates: list[dict[str, Any]] = []
    best_score = 0.0
    best_contig = 0
    for w in wmap.get("witnesses") or []:
        preview = str(w.get("text_preview") or "")
        score = float(w.get("mapping_score") or 0)
        contig = int(w.get("contiguous_substring_len") or 0)
        opening_hits = _opening_hit_count(preview)
        best_score = max(best_score, score)
        best_contig = max(best_contig, contig)
        candidates.append(
            {
                "witness_id": w.get("witness_id"),
                "scroll": w.get("scroll"),
                "line": w.get("line"),
                "mapping_score": score,
                "contiguous_substring_len": contig,
                "mt_v2_opening_token_hits": opening_hits,
                "mapping_status": w.get("mapping_status"),
                "ps_5_2_direct_line_candidate": contig >= 8 and opening_hits >= 3,
                "text_preview": preview[:120],
            }
        )

    shadow = {
        "rail": "commander_verified_shadow_witness",
        "scroll": e13_intake.get("scroll"),
        "fragment": e13_intake.get("fragment"),
        "line": e13_intake.get("line"),
        "shadow_verse_anchor": e13_intake.get("shadow_verse_anchor"),
        "witness_id": e13_intake.get("witness_id"),
        "qd_url": e13_intake.get("evidence_url") or QD_4Q98B_URL,
        "external_verse_scope": e13_intake.get("external_verse_scope") or QD_VERSE_SCOPE,
        "note": "Shadow rail is NOT Ps.5.2 v.2 direct line proof.",
    }

    direct_candidates = [c for c in candidates if c.get("ps_5_2_direct_line_candidate")]
    verified_anchor_achieved = len(direct_candidates) > 0

    findings = [
        {
            "id": "V1",
            "claim": "MT Ps.5.2 v.2 opening (אמרי/האזינה/בינה/הגיגי) has no DSS line with contiguous match in local 4Q pool",
            "status": "gap_confirmed",
            "evidence": {"best_contiguous_substring_len": best_contig, "best_mapping_score": best_score},
        },
        {
            "id": "V2",
            "claim": "QD 4Q98b frg.1 line 1 aligns with Ps 5:8-9 not MT Ps.5.2 v.2",
            "status": "external_source_confirmed",
            "evidence": {"qd_url": QD_4Q98B_URL, "verse_scope": QD_VERSE_SCOPE},
        },
        {
            "id": "V3",
            "claim": "11Q5 bench retired; no consulted open 11Q5 transcription exposes Ps.5.2 direct verse line",
            "status": "prior_bench_retired",
        },
        {
            "id": "V4",
            "claim": "CROSS_REF ENTRY_13 remains commander_verified_shadow_witness without verified_anchor",
            "status": "cross_ref_aligned",
            "evidence": {"satellite_status": "commander_verified_shadow_witness" in str(e13_cross.get("satellite_ref", ""))},
        },
    ]

    return {
        "schema": "entry_13_ps5_2_verified_anchor_evidence_packet_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "send_gate": "HOLD",
        "entry_id": "ENTRY_13",
        "bench_canonical_ref": "Ps.5.2",
        "target_status": "verified_anchor",
        "verified_anchor_achieved": verified_anchor_achieved,
        "mt_canon": canon,
        "shadow_rail": shadow,
        "witness_candidate_scan": {
            "pool_rows": len(candidates),
            "direct_line_candidates": len(direct_candidates),
            "best_mapping_score": best_score,
            "best_contiguous_substring_len": best_contig,
            "rows": candidates,
        },
        "external_sources": [
            {
                "source": "Qumran-Digital 4Q98b",
                "url": QD_4Q98B_URL,
                "edition": "Ulrich et al., DJD XVI (4QPss)",
                "attested_scope": QD_VERSE_SCOPE,
                "mt_ps_5_2_v2_attested": False,
            },
            {
                "source": "etcbc-dss local align pool",
                "path": str(MAP_4Q.relative_to(ROOT)),
                "scrolls": wmap.get("scrolls") or [],
                "mt_ps_5_2_v2_attested": False,
            },
        ],
        "findings": findings,
        "promotion_blockers": [
            "no_dss_line_with_ps_5_2_v2_contiguous_hebrew",
            "qd_4q98b_scope_starts_ps_5_8",
            "11q5_bench_retired",
        ],
        "next_evidence_needed": [
            "primary edition line ref mapping MT Ps.5.2 v.2 to a DSS fragment line (if extant)",
            "independent DJD/QD col-line citation for v.2 not only 5:8+",
        ],
        "reproduce": "py scripts/build_entry_13_ps5_2_verified_anchor_evidence_packet_v1.py",
    }


def _md(doc: dict[str, Any]) -> str:
    mt = doc.get("mt_canon") or {}
    sh = doc.get("shadow_rail") or {}
    scan = doc.get("witness_candidate_scan") or {}
    lines = [
        "# ENTRY_13 — MT Ps.5.2 verified_anchor 증거 패킷",
        "",
        f"- 생성: {doc.get('generated_at_utc')}",
        f"- **verified_anchor 달성: {doc.get('verified_anchor_achieved')}**",
        f"- SEND: **{doc.get('send_gate')}**",
        "",
        "## MT bench (Ps.5.2 v.2)",
        "",
        f"- verse_id: `{mt.get('verse_id')}`",
        f"- hebrew (canon): {mt.get('hebrew_text')}",
        f"- gematria: {mt.get('gematria_hebrew')}",
        "",
        "## Shadow rail (별도 — 혼동 금지)",
        "",
        f"- status: **{sh.get('rail')}**",
        f"- scroll: **{sh.get('scroll')}** frg.{sh.get('fragment')} line {sh.get('line')}",
        f"- shadow anchor: **{sh.get('shadow_verse_anchor')}**",
        f"- QD scope: {sh.get('external_verse_scope')}",
        f"- URL: {sh.get('qd_url')}",
        "",
        "## 로컬 4Q witness 스캔",
        "",
        f"- pool rows: **{scan.get('pool_rows')}**",
        f"- Ps.5.2 v.2 direct candidates: **{scan.get('direct_line_candidates')}**",
        f"- best mapping_score: **{scan.get('best_mapping_score')}**",
        f"- best contiguous_substring_len: **{scan.get('best_contiguous_substring_len')}**",
        "",
        "## Findings",
        "",
    ]
    for f in doc.get("findings") or []:
        lines.append(f"- **{f.get('id')}** {f.get('claim')} → `{f.get('status')}`")
    lines.extend(
        [
            "",
            "## 결론",
            "",
            "MT Ps.5.2 **직접 행** `verified_anchor`는 현재 증거로 **미달성**. "
            "4Q98b는 Ps 5:8–9 shadow witness로만 승격됨.",
            "",
            "## 재현",
            "",
            "```powershell",
            "py scripts/build_entry_13_ps5_2_verified_anchor_evidence_packet_v1.py",
            "```",
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
                "verified_anchor_achieved": doc["verified_anchor_achieved"],
                "pool_rows": doc["witness_candidate_scan"]["pool_rows"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
