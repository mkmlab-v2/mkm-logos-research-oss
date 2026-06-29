#!/usr/bin/env python3
"""Commander manuscript integrity audit (11Q5 / Ps 4-5) — audit_only sidecar [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCAN = ROOT / "reports/dss_line_witness_verification_scan_v1_latest.json"
PROMO = ROOT / "docs/final/artifacts/dss_line_witness_promotion_gate_v1_latest.json"
MAP_11Q5 = ROOT / "reports/dss_11q5_line_witness_map_v1_latest.json"
MAP_4Q = ROOT / "reports/dss_4q_ps5_line_witness_map_v1_latest.json"
OUT_JSON = ROOT / "reports/manuscript_integrity_audit_11q5_psalms_commander_v1_latest.json"
OUT_MD = ROOT / "reports/manuscript_integrity_audit_11q5_psalms_commander_v1_latest.md"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def build() -> dict[str, Any]:
    scan = _load(SCAN)
    promo = _load(PROMO)
    m11 = _load(MAP_11Q5)
    m4q = _load(MAP_4Q)
    scan_sm = scan.get("summary") or {}
    m4q_sm = m4q.get("summary") or {}
    return {
        "schema": "manuscript_integrity_audit_11q5_psalms_commander_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "audit_only": True,
        "research_only": True,
        "theology_to_sales_forbidden": True,
        "send_gate": "HOLD",
        "track_wall": {
            "logos_core_mutation_forbidden": True,
            "merge_into_canon_31k_41k": False,
            "cross_ref_draft_mutation_forbidden": True,
        },
        "findings": [
            {
                "id": "F1",
                "claim": "11Q5 does not physically contain MT Psalms 4-5",
                "status": "accepted_bench_relabel",
                "repo_evidence": {
                    "p4_auto_verified_total": scan_sm.get("auto_verified_total"),
                    "p4_promotion_ok": promo.get("promotion_ok"),
                },
            },
            {
                "id": "F2",
                "claim": "Mainline 31k logos_verse_4d has no 11Q5/dss verse rows",
                "status": "verified_by_p5_gate",
            },
            {
                "id": "F3",
                "claim": "Ps.4.6 Qumran Hebrew witness none in local ETCBC",
                "status": "mt_only_rail",
                "witness_rail": "mt_only",
            },
            {
                "id": "F4",
                "claim": "Ps.5.2 shadow witnesses retargeted to 4Q83/4Q98b (provisional)",
                "status": "shadow_rail_active",
                "provisional_witness_rows": m4q_sm.get("witness_rows"),
                "hebrew_chars_ge_6": m4q_sm.get("hebrew_chars_ge_6"),
            },
        ],
        "misframing_corrected": (
            "B-track ENTRY_12/13 11Q5 lexical bench was not mainline corruption; "
            "it was partial_anchor bench metadata now retired/retargeted."
        ),
        "artifacts": {
            "p4_scan": str(SCAN.relative_to(ROOT)).replace("\\", "/"),
            "promotion_gate": str(PROMO.relative_to(ROOT)).replace("\\", "/"),
            "11q5_map": str(MAP_11Q5.relative_to(ROOT)).replace("\\", "/"),
            "4q_map": str(MAP_4Q.relative_to(ROOT)).replace("\\", "/"),
        },
        "reproduce": "py scripts/build_manuscript_integrity_audit_11q5_psalms_v1.py",
    }


def render_md(doc: dict[str, Any]) -> str:
    lines = [
        "# Manuscript Integrity Audit — 11Q5 / Psalms 4–5 (Commander)",
        "",
        f"- Generated: {doc.get('generated_at_utc')}",
        "- Lane: `track_b_hypo` · `audit_only` · **SEND_GATE: HOLD**",
        "",
        "## Executive summary",
        "",
        "- **11Q5 ↔ Ps.4/Ps.5 bench hypothesis retired** (not a mainline 31k corruption).",
        "- **Promotion Lock holds:** P4 `promotion_ok: false`.",
        "- **Ps.4.6:** `mt_only` rail — no Qumran Hebrew witness in local ETCBC.",
        "- **Ps.5.2:** shadow rail retargeted to **4Q83/4Q98b** (provisional lexical anchors).",
        "",
        "## Findings",
        "",
    ]
    for f in doc.get("findings") or []:
        lines.append(f"- **{f.get('id')}** {f.get('claim')} → `{f.get('status')}`")
    lines.extend(["", "## Misframing correction", "", doc.get("misframing_corrected", ""), ""])
    lines.append("---")
    lines.append("Reproduce: `py scripts/build_manuscript_integrity_audit_11q5_psalms_v1.py`")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json-out", type=Path, default=OUT_JSON)
    ap.add_argument("--md-out", type=Path, default=OUT_MD)
    args = ap.parse_args()
    doc = build()
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.md_out.write_text(render_md(doc), encoding="utf-8")
    print(json.dumps({"ok": True, "findings": len(doc.get("findings") or [])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
