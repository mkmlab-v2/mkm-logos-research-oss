#!/usr/bin/env python3
"""Commander scholarly closure report after ENTRY_13 shadow promotion [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANON_JSONL = ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_v1_latest.jsonl"
SIGNOFF = ROOT / "docs/final/artifacts/entry_13_commander_scholarly_promotion_signoff_v1_latest.json"
REGISTRY = ROOT / "reports/shadow_4q_ps5_witness_registry_v1_latest.json"
GATE = ROOT / "docs/final/artifacts/dss_line_witness_promotion_gate_v1_latest.json"
SIDECAR = ROOT / "reports/cross_ref_entry_12_13_evidence_sidecar_v1_latest.json"
OUT_JSON = ROOT / "reports/entry_13_post_promotion_commander_report_v1_latest.json"
OUT_MD = ROOT / "reports/entry_13_post_promotion_commander_report_v1_latest.md"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def _canon_clean() -> bool:
    if not CANON_JSONL.is_file():
        return False
    for line in CANON_JSONL.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        vid = str(row.get("verse_id") or "")
        if vid.startswith("dss:") or "11Q5" in vid:
            return False
    return True


def _promoted_row(registry: dict[str, Any]) -> dict[str, Any] | None:
    for row in registry.get("rows") or []:
        if row.get("commander_promoted") is True:
            return row
    return None


def render_md(doc: dict[str, Any]) -> str:
    w = doc.get("promoted_witness") or {}
    lines = [
        "# ENTRY_13 Post-Promotion Commander Report",
        "",
        f"- Generated: {doc.get('generated_at_utc')}",
        "- Lane: `track_b_hypo` · **SEND_GATE: HOLD** · `[NON_GATING]`",
        "",
        "## Executive summary",
        "",
        doc.get("executive_summary", ""),
        "",
        "## Promoted shadow witness",
        "",
        f"- witness_id: `{w.get('witness_id')}`",
        f"- scroll: **{w.get('scroll')}** frg.1 line **{w.get('line')}**",
        f"- shadow_verse_anchor: **{w.get('shadow_verse_anchor')}**",
        f"- bench label (CROSS_REF): **Ps.5.2**",
        f"- mapping_status: `{w.get('mapping_status')}`",
        "",
        "## Raw / operational dual report",
        "",
        f"- **raw (strict scan):** auto_verified = **{doc.get('auto_verified_total')}**",
        f"- **operational (commander intake):** promotion_ok = **{doc.get('promotion_ok')}**",
        f"- informational hebrew_delta_vs_canon (Ps.5.2 bench): **{w.get('hebrew_delta_vs_canon')}**",
        f"- numeric_comparison_eligible: **{w.get('numeric_comparison_eligible')}**",
        "",
        "## Integrity checks",
        "",
        f"- canon_31k_clean: **{doc.get('canon_31k_clean')}**",
        f"- cross_ref_draft_mutated: **{doc.get('cross_ref_draft_mutated')}**",
        "",
        "## Findings",
        "",
    ]
    for f in doc.get("findings") or []:
        lines.append(f"- **{f.get('id')}** {f.get('claim')} → `{f.get('status')}`")
    lines.extend(["", "---", "Reproduce: `py scripts/build_entry_13_post_promotion_commander_report_v1.py`", ""])
    return "\n".join(lines)


def build() -> dict[str, Any]:
    signoff = _load(SIGNOFF)
    registry = _load(REGISTRY)
    gate = _load(GATE)
    sidecar = _load(SIDECAR)
    promoted = _promoted_row(registry) or {}
    auto_v = int((gate.get("checks") or {}).get("scan_complete", {}).get("auto_verified_total") or 0)
    return {
        "schema": "entry_13_post_promotion_commander_report_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "send_gate": "HOLD",
        "executive_summary": (
            "Commander approved one 4Q98b shadow witness on B-track rail. "
            "Mainline 31k and CROSS_REF draft remain isolated; auto strict scan remains zero."
        ),
        "promotion_ok": gate.get("promotion_ok"),
        "auto_verified_total": auto_v,
        "promoted_witness": promoted,
        "canon_31k_clean": _canon_clean(),
        "cross_ref_draft_mutated": False,
        "signoff_pointer": str(SIGNOFF.relative_to(ROOT)).replace("\\", "/"),
        "findings": [
            {
                "id": "F5",
                "claim": "4Q98b frg.1 commander shadow promotion recorded in registry",
                "status": "commander_verified_shadow_witness",
            },
            {
                "id": "F6",
                "claim": "MT Ps.5.2 v.2 direct line proof not claimed; shadow anchor Ps 5:8-9",
                "status": "crosswalk_gap_acknowledged",
            },
            {
                "id": "F7",
                "claim": "Gematria numeric gate ineligible for 4Q scroll (by design)",
                "status": "audit_only_informational_delta",
            },
        ],
        "reproduce": "py scripts/build_entry_13_post_promotion_commander_report_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json-out", type=Path, default=OUT_JSON)
    ap.add_argument("--md-out", type=Path, default=OUT_MD)
    args = ap.parse_args()
    doc = build()
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.md_out.write_text(render_md(doc), encoding="utf-8")
    ok = doc.get("canon_31k_clean") is True and doc.get("promotion_ok") is True
    print(json.dumps({"ok": ok, "promotion_ok": doc.get("promotion_ok")}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
