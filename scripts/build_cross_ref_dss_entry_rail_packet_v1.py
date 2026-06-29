#!/usr/bin/env python3
"""Per-entry DSS CROSS_REF rail evidence packet (ENTRY_01–16 sequential) [HYPO]."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CROSS = ROOT / "docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json"

ENTRY_CONFIG: dict[str, dict[str, Any]] = {
    "ENTRY_01": {
        "scroll": "1QM 1:1-7 (War Scroll, Col.1)",
        "dss_doc": "docs/final/btrack_dss_1QM_col1_excerpt.md",
        "rail_target": "thematic_bench_documented",
        "waiting_queue": False,
        "thematic": True,
    },
    "ENTRY_02": {
        "scroll": "1Enoch 10:4-6",
        "dss_doc": "docs/final/btrack_apocrypha_1enoch_ch10_excerpt.md",
        "rail_target": "parallel_corpus_thematic",
        "waiting_queue": False,
        "thematic": True,
    },
    "ENTRY_03": {
        "scroll": "1Enoch 10:7",
        "dss_doc": "docs/final/btrack_apocrypha_1enoch_judgment_pure.md",
        "rail_target": "parallel_corpus_thematic",
        "waiting_queue": False,
        "thematic": True,
    },
    "ENTRY_04": {
        "scroll": "Jubilees 6:29-38 + 364-day",
        "dss_doc": "docs/final/btrack_apocrypha_jubilees_ch6_excerpt_charles.md",
        "rail_target": "temporal_bench_documented",
        "waiting_queue": False,
        "thematic": True,
    },
    "ENTRY_05": {
        "scroll": "1QS IX 10-11",
        "dss_doc": "docs/final/btrack_dss_1QS_sectarian_context.md",
        "rail_target": "thematic_bench_documented",
        "waiting_queue": False,
        "thematic": True,
    },
    "ENTRY_06": {
        "scroll": "1QpHab (1Q15)",
        "dss_doc": "docs/final/btrack_dss_1QpHab_col7.md",
        "qd_url": "https://lexicon.qumran-digital.org/transcriptions/1QpHab/2024-04-29/index.html",
        "rail_target": "partial_verified_maintained",
        "waiting_queue": False,
    },
    "ENTRY_07": {
        "scroll": "11QT (11Q19)",
        "dss_doc": "docs/final/btrack_dss_11QT_temple.md",
        "rail_target": "waiting_queue_open",
        "waiting_queue": True,
        "blocker": "public_line_level_transcription_unavailable",
    },
    "ENTRY_08": {
        "scroll": "4Q319 (4QOtot)",
        "dss_doc": "docs/final/btrack_dss_4Q319_otot.md",
        "rail_target": "waiting_queue_open",
        "waiting_queue": True,
        "blocker": "fragment_line_transcription_unavailable",
    },
    "ENTRY_09": {
        "scroll": "4Q169 (4QpNah)",
        "dss_doc": "docs/final/btrack_dss_4Q169_pesh_nah.md",
        "qd_url": "https://lexicon.qumran-digital.org/transcriptions/4Q169/2025-03-11/index.html",
        "rail_target": "partial_verified_maintained",
        "waiting_queue": False,
    },
    "ENTRY_10": {
        "scroll": "CD-A / 4Q266-273",
        "dss_doc": "docs/final/btrack_dss_cd_damascus_boundary.md",
        "qd_url": "https://lexicon.qumran-digital.org/transcriptions/4Q267/2023-10-25/index.html",
        "rail_target": "partial_verified_maintained",
        "waiting_queue": False,
        "blocker": "cd_a_direct_line_crosswalk_tbd",
    },
    "ENTRY_11": {
        "scroll": "1QM.1.1",
        "dss_doc": "docs/final/btrack_dss_1QM_col1_excerpt.md",
        "rail_target": "hypo_analogy_hold",
        "waiting_queue": False,
        "hypo": True,
    },
    "ENTRY_12": {
        "scroll": "MT-only",
        "dss_doc": "docs/final/btrack_dss_11Q5_psalms.md",
        "rail_target": "closed_p9",
        "waiting_queue": False,
    },
    "ENTRY_13": {
        "scroll": "4Q98b",
        "dss_doc": "reports/entry_13_ps5_2_verified_anchor_evidence_packet_v1_latest.json",
        "rail_target": "closed_p9_shadow",
        "waiting_queue": False,
    },
    "ENTRY_14": {
        "scroll": "4QDeut (4Q129)",
        "dss_doc": "docs/final/btrack_dss_deut_raw.md",
        "qd_url": "https://lexicon.qumran-digital.org/transcriptions/4Q129/2024-07-30/index.html",
        "rail_target": "partial_verified_maintained",
        "waiting_queue": False,
    },
    "ENTRY_15": {
        "scroll": "4QGen (b-k)",
        "dss_doc": None,
        "rail_target": "partial_verified_maintained",
        "waiting_queue": False,
        "blocker": "gen_49_19_direct_fragment_line_tbd",
    },
    "ENTRY_16": {
        "scroll": "Ezra-Neh (4Q117 partial)",
        "dss_doc": None,
        "qd_url": "https://lexicon.qumran-digital.org/transcriptions/4Q117/2024-07-30/index.html",
        "rail_target": "missing_anchor_documented",
        "waiting_queue": True,
        "blocker": "no_extant_dss_witness_ezra_2_54",
    },
}

ENTRY_ORDER = [
    "ENTRY_01",
    "ENTRY_02",
    "ENTRY_03",
    "ENTRY_04",
    "ENTRY_05",
    "ENTRY_06",
    "ENTRY_07",
    "ENTRY_08",
    "ENTRY_09",
    "ENTRY_10",
    "ENTRY_11",
    "ENTRY_12",
    "ENTRY_13",
    "ENTRY_14",
    "ENTRY_15",
    "ENTRY_16",
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _entry_row(cross: dict[str, Any], entry_id: str) -> dict[str, Any]:
    return next(e for e in cross.get("entries") or [] if e.get("entry_id") == entry_id)


def _status_from_sat(sat: str) -> str:
    if "status=verified_anchor" in sat:
        return "verified_anchor"
    if "status=commander_verified_shadow_witness" in sat:
        return "commander_verified_shadow_witness"
    if "status=mt_only_no_qumran_witness" in sat:
        return "mt_only_no_qumran_witness"
    if "status=missing_anchor_until_source_update" in sat:
        return "missing_anchor_until_source_update"
    if "partial_anchor_verified" in sat:
        return "partial_anchor_verified"
    if "analogy_bench" in sat or "[HYPO]" in sat:
        return "hypo_analogy_bench"
    return "thematic_bench"


def build_entry(entry_id: str) -> dict[str, Any]:
    cross = _load(CROSS)
    row = _entry_row(cross, entry_id)
    cfg = ENTRY_CONFIG[entry_id]
    sat = str(row.get("satellite_ref") or "")
    status = _status_from_sat(sat)
    verified = status == "verified_anchor"
    return {
        "schema": "cross_ref_dss_entry_rail_packet_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "entry_id": entry_id,
        "canonical_ref": row.get("canonical_ref"),
        "state_candidate_id": row.get("state_candidate_id"),
        "scroll": cfg.get("scroll"),
        "satellite_status": status,
        "verified_anchor_achieved": verified,
        "rail_target": cfg.get("rail_target"),
        "rail_closed": cfg.get("rail_target", "").startswith("closed_p9"),
        "waiting_queue": cfg.get("waiting_queue", False),
        "hypo": cfg.get("hypo", False),
        "thematic": cfg.get("thematic", False),
        "blocker": cfg.get("blocker"),
        "dss_doc": cfg.get("dss_doc"),
        "qd_url": cfg.get("qd_url"),
        "satellite_ref_excerpt": sat[:220] + ("…" if len(sat) > 220 else ""),
        "cross_ref_artifact_path": row.get("artifact_path"),
        "send_gate": "HOLD",
        "non_gating": True,
        "research_only": True,
    }


def build_registry() -> dict[str, Any]:
    packets = [build_entry(eid) for eid in ENTRY_ORDER]
    closed = sum(1 for p in packets if p.get("rail_closed"))
    verified_n = sum(1 for p in packets if p.get("verified_anchor_achieved"))
    waiting = sum(1 for p in packets if p.get("waiting_queue"))
    return {
        "schema": "cross_ref_dss_entry_rail_registry_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "entry_order": ENTRY_ORDER,
        "summary": {
            "entries": len(packets),
            "rail_closed": closed,
            "verified_anchor_achieved": verified_n,
            "waiting_queue_open": waiting,
            "partial_or_documented": len(packets) - closed - verified_n,
        },
        "packets": packets,
        "reproduce": "py scripts/build_cross_ref_dss_entry_rail_packet_v1.py --all",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--entry-id", help="Single ENTRY_* id")
    ap.add_argument("--all", action="store_true")
    ap.add_argument(
        "--registry-out",
        type=Path,
        default=ROOT / "docs/final/artifacts/cross_ref_dss_entry_rail_registry_v1_latest.json",
    )
    args = ap.parse_args()
    if not args.all and not args.entry_id:
        print(json.dumps({"ok": False, "reason": "pass --all or --entry-id"}, ensure_ascii=False))
        return 1
    if args.entry_id:
        eid = args.entry_id.strip().upper()
        if eid not in ENTRY_CONFIG:
            print(json.dumps({"ok": False, "reason": "unknown_entry"}, ensure_ascii=False))
            return 1
        doc = build_entry(eid)
        out = ROOT / f"reports/cross_ref_dss_entry_{eid.lower()}_rail_packet_v1_latest.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "entry_id": eid, "out": str(out.relative_to(ROOT))}, ensure_ascii=False))
        return 0
    reg = build_registry()
    args.registry_out.parent.mkdir(parents=True, exist_ok=True)
    args.registry_out.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for p in reg["packets"]:
        eid = p["entry_id"]
        out = ROOT / f"reports/cross_ref_dss_entry_{eid.lower()}_rail_packet_v1_latest.json"
        out.write_text(json.dumps(p, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path = ROOT / "reports/cross_ref_dss_entry_sequential_rail_summary_v1_latest.md"
    lines = [
        "# CROSS_REF DSS Entry Sequential Rail (ENTRY_01–16)",
        "",
        f"- Generated: {reg['generated_at_utc']}",
        f"- Entries: **{reg['summary']['entries']}** · closed: **{reg['summary']['rail_closed']}**",
        f"- verified_anchor: **{reg['summary']['verified_anchor_achieved']}** · waiting: **{reg['summary']['waiting_queue_open']}**",
        "",
        "| Entry | Canon | Status | Rail target |",
        "| --- | --- | --- | --- |",
    ]
    for p in reg["packets"]:
        lines.append(
            f"| {p['entry_id']} | {p.get('canonical_ref')} | {p.get('satellite_status')} | {p.get('rail_target')} |"
        )
    lines.extend(["", "Reproduce: `py scripts/build_cross_ref_dss_entry_rail_packet_v1.py --all`", ""])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"ok": True, "summary": reg["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
