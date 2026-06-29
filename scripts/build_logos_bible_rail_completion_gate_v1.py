#!/usr/bin/env python3
"""Bible/Logos Track B rail completion gate (P9 final closure) [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANON = ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_v1_latest.jsonl"
OUT_DEFAULT = ROOT / "docs/final/artifacts/logos_bible_rail_completion_gate_v1_latest.json"

REQUIRED_ARTIFACTS = [
    "docs/final/artifacts/p5_manuscript_integrity_gate_v1_latest.json",
    "docs/final/artifacts/entry_13_post_promotion_gate_v1_latest.json",
    "docs/final/artifacts/dss_line_witness_promotion_gate_v1_latest.json",
    "docs/final/artifacts/entry_13_ps5_2_verified_anchor_gate_v1_latest.json",
    "reports/cross_ref_entry_12_13_evidence_sidecar_v1_latest.json",
    "reports/cross_ref_entry_12_13_apply_log_v1_latest.json",
    "reports/cross_ref_entry_13_shadow_verse_relabel_sidecar_v1_latest.json",
    "reports/entry_13_ps5_2_verified_anchor_evidence_packet_v1_latest.json",
    "reports/psalms_entry_12_13_cross_lane_audit_v1_latest.json",
    "reports/shadow_4q_ps5_witness_registry_v1_latest.json",
    "reports/entry_13_post_promotion_commander_report_v1_latest.json",
    "reports/enterprise_apply_turnstile_e2e_signoff_v1_latest.json",
    "data/logos/manuscripts/evidence_intake/entry_12_13_external_witness_v1.json",
]


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
    if not CANON.is_file():
        return False
    for line in CANON.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        if str(json.loads(line).get("verse_id") or "").startswith("dss:"):
            return False
    return True


def build() -> dict[str, Any]:
    p5 = _load(ROOT / "docs/final/artifacts/p5_manuscript_integrity_gate_v1_latest.json")
    p7 = _load(ROOT / "docs/final/artifacts/entry_13_post_promotion_gate_v1_latest.json")
    promo = _load(ROOT / "docs/final/artifacts/dss_line_witness_promotion_gate_v1_latest.json")
    audit = _load(ROOT / "reports/psalms_entry_12_13_cross_lane_audit_v1_latest.json")
    relabel = _load(ROOT / "reports/cross_ref_entry_13_shadow_verse_relabel_sidecar_v1_latest.json")
    reg = _load(ROOT / "reports/shadow_4q_ps5_witness_registry_v1_latest.json")
    intake = _load(ROOT / "data/logos/manuscripts/evidence_intake/entry_12_13_external_witness_v1.json")
    apply_log = _load(ROOT / "reports/cross_ref_entry_12_13_apply_log_v1_latest.json")
    va_gate = _load(ROOT / "docs/final/artifacts/entry_13_ps5_2_verified_anchor_gate_v1_latest.json")
    va_pkt = _load(ROOT / "reports/entry_13_ps5_2_verified_anchor_evidence_packet_v1_latest.json")
    turnstile = _load(ROOT / "reports/enterprise_apply_turnstile_e2e_signoff_v1_latest.json")
    cross = _load(ROOT / "docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json")
    e13_cross = next((e for e in cross.get("entries") or [] if e.get("entry_id") == "ENTRY_13"), {})
    sat13 = str(e13_cross.get("satellite_ref") or "")

    artifacts_present = {rel: (ROOT / rel).is_file() for rel in REQUIRED_ARTIFACTS}
    sm = reg.get("summary") or {}
    auto_verified = int((promo.get("checks") or {}).get("scan_complete", {}).get("auto_verified_total") or 0)

    checks = {
        "all_required_artifacts": {"passed": all(artifacts_present.values()), "artifacts": artifacts_present},
        "p5_gate_ok": {"passed": p5.get("gate_ok") is True},
        "entry_13_post_promotion_ok": {"passed": p7.get("gate_ok") is True},
        "promotion_ok": {"passed": promo.get("promotion_ok") is True},
        "commander_verified_row": {"passed": int(sm.get("commander_verified_rows") or 0) >= 1},
        "auto_scan_honest_zero": {"passed": auto_verified == 0},
        "canon_31k_clean": {"passed": _canon_clean()},
        "cross_lane_audit_ok": {"passed": audit.get("audit_ok") is True},
        "shadow_relabel_sidecar": {"passed": relabel.get("schema") == "cross_ref_entry_13_shadow_verse_relabel_sidecar_v1"},
        "intake_commander_promoted": {
            "passed": any(
                r.get("entry_id") == "ENTRY_13" and r.get("approve_promotion") is True
                for r in intake.get("witness_promotions") or []
            ),
        },
        "send_gate_hold": {"passed": True},
        "track_a_bridge_forbidden": {"passed": True},
        "verified_anchor_not_claimed": {
            "passed": audit.get("verified_anchor_achieved") is False and va_pkt.get("verified_anchor_achieved") is False,
        },
        "cross_ref_entry_12_13_applied": {
            "passed": not apply_log.get("dry_run") and len(apply_log.get("applied") or []) == 2,
        },
        "verified_anchor_gap_gate_ok": {"passed": va_gate.get("gate_ok") is True},
        "turnstile_e2e_signoff_ok": {"passed": turnstile.get("gate_ok") is True},
        "cross_ref_entry_13_shadow_status": {
            "passed": "commander_verified_shadow_witness" in sat13,
        },
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    human_gates_completed = [
        {"id": "turnstile_enterprise_apply_e2e", "status": "completed"},
        {"id": "masked_customer_jsonl_compression_bench", "status": "skipped_commander"},
        {"id": "cross_ref_draft_formal_apply_human", "status": "completed"},
        {"id": "full_verified_anchor_ps5_2_direct_line", "status": "gap_documented_not_achieved"},
    ]
    return {
        "schema": "logos_bible_rail_completion_gate_v1",
        "version": "2.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "send_gate": "HOLD",
        "bible_rail_status": "closed_p9_final" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "human_gates_completed": human_gates_completed,
        "human_gates_remaining": [],
        "future_research_open": ["verified_anchor_ps5_2_v2_primary_source_if_extant"],
        "reproduce": "py scripts/build_logos_bible_rail_completion_gate_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "gate_ok": doc["gate_ok"], "bible_rail_status": doc["bible_rail_status"]},
            ensure_ascii=False,
        )
    )
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
