#!/usr/bin/env python3
"""Operator board for ENTRY_12/13 verification promotion workflow [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "reports/cross_ref_entry_12_13_evidence_sidecar_v1_latest.json"
SCAN = ROOT / "reports/dss_line_witness_verification_scan_v1_latest.json"
GATE = ROOT / "docs/final/artifacts/dss_line_witness_promotion_gate_v1_latest.json"
P5_GATE = ROOT / "docs/final/artifacts/p5_manuscript_integrity_gate_v1_latest.json"
POST_GATE = ROOT / "docs/final/artifacts/entry_13_post_promotion_gate_v1_latest.json"
REGISTRY_4Q = ROOT / "reports/shadow_4q_ps5_witness_registry_v1_latest.json"
MAP_4Q = ROOT / "reports/dss_4q_ps5_line_witness_map_v1_latest.json"
AUDIT = ROOT / "reports/manuscript_integrity_audit_11q5_psalms_commander_v1_latest.json"
OUT_MD = ROOT / "reports/dss_line_witness_verification_operator_board_v1_latest.md"
OUT_JSON = ROOT / "reports/dss_line_witness_verification_operator_board_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def render_md(doc: dict[str, Any]) -> str:
    lines = [
        "# DSS Line Witness Verification Operator Board (ENTRY_12/13)",
        "",
        f"- Generated: {doc.get('generated_at_utc')}",
        "- Lane: `track_b_hypo` · **SEND_GATE: HOLD**",
        "",
        "## Status",
        "",
        f"- P5 manuscript integrity gate: **{doc.get('p5_manuscript_integrity_gate_ok')}**",
        f"- Infrastructure gate: **{doc.get('infrastructure_gate_ok')}**",
        f"- Promotion ready: **{doc.get('promotion_ok')}**",
        f"- Auto-verified (strict scan): **{doc.get('auto_verified_total')}**",
        f"- ENTRY_13 4Q provisional rows: **{doc.get('entry_13_4q_provisional_rows')}**",
        f"- ENTRY_13 commander verified: **{doc.get('entry_13_commander_verified_rows')}**",
        f"- Post-promotion gate: **{doc.get('entry_13_post_promotion_gate_ok')}**",
        f"- 11Q5 bench: **{doc.get('eleven_q5_bench_status')}**",
        "",
        "## Commander actions (manual path)",
        "",
        "### ENTRY_12 · Ps.4.6 (`mt_only`)",
        "1. **No action required** for 11Q5 — bench hypothesis **retired**.",
        "2. Optional: document external edition if a future Qumran witness is published.",
        "",
        "### ENTRY_13 · Ps.5.2 (`4Q83` / `4Q98b` shadow)",
        "1. Obtain col/line anchor from DJD IV or Qumran-Digital for **4Q83/4Q98b** (not 11Q5).",
        "2. Copy template → `data/logos/manuscripts/evidence_intake/entry_12_13_external_witness_v1.json`.",
        "3. Set `witness_id` from 4Q map, `scroll`, `line`, `edition_ref`, `evidence_url`, `approve_promotion: true`.",
        "4. Re-run: `py scripts/run_dss_line_witness_verification_chain_v1.py --apply-promotion`",
        "",
        "## Per-entry",
        "",
    ]
    for e in doc.get("entries") or []:
        lines.extend(
            [
                f"### {e.get('entry_id')} · {e.get('canonical_ref')}",
                f"- Witness rail: `{e.get('witness_rail')}`",
                f"- Bench status: `{e.get('bench_status')}`",
                f"- Current: `{e.get('current_anchor_status')}`",
                f"- Target: `{e.get('target_anchor_status')}`",
                f"- Auto verified: {e.get('auto_scan_verified_count')}",
                f"- Provisional witnesses: {e.get('p3_provisional_witness_count')}",
                f"- Waiting reason: {e.get('waiting_queue_reason')}",
                "",
            ]
        )
    lines.append("---")
    lines.append("Reproduce: `py scripts/build_dss_line_witness_operator_board_v1.py`")
    return "\n".join(lines) + "\n"


def build() -> dict[str, Any]:
    sidecar = _load(SIDECAR)
    scan = _load(SCAN)
    gate = _load(GATE)
    p5 = _load(P5_GATE)
    map_4q = _load(MAP_4Q)
    reg4 = _load(REGISTRY_4Q)
    post = _load(POST_GATE)
    audit = _load(AUDIT)
    reg_sm = reg4.get("summary") or {}
    return {
        "schema": "dss_line_witness_verification_operator_board_v1",
        "version": "1.2.0",
        "generated_at_utc": _utc(),
        "p5_manuscript_integrity_gate_ok": p5.get("gate_ok"),
        "entry_13_post_promotion_gate_ok": post.get("gate_ok"),
        "eleven_q5_bench_status": "hypothesis_retired",
        "infrastructure_gate_ok": gate.get("gate_ok"),
        "promotion_ok": gate.get("promotion_ok"),
        "promotion_pending_external": gate.get("promotion_pending_external"),
        "auto_verified_total": (scan.get("summary") or {}).get("auto_verified_total"),
        "entry_13_4q_provisional_rows": (map_4q.get("summary") or {}).get("provisional_lexical_anchor_rows"),
        "entry_13_commander_verified_rows": reg_sm.get("commander_verified_rows"),
        "shadow_verse_anchor": reg4.get("shadow_verse_anchor"),
        "commander_audit_findings": len(audit.get("findings") or []),
        "entries": sidecar.get("entries") or [],
        "intake_template": "data/logos/manuscripts/evidence_intake/entry_12_13_external_witness_v1.template.json",
        "reproduce": "py scripts/build_dss_line_witness_operator_board_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--md-out", type=Path, default=OUT_MD)
    ap.add_argument("--json-out", type=Path, default=OUT_JSON)
    args = ap.parse_args()

    doc = build()
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.md_out.write_text(render_md(doc), encoding="utf-8")
    ok = doc.get("infrastructure_gate_ok") is True and doc.get("p5_manuscript_integrity_gate_ok") is True
    print(json.dumps({"ok": ok, "promotion_pending_external": doc.get("promotion_pending_external")}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
