from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_external_validation_ms_evidence_pack_v1 as mod


def test_build_external_validation_ms_evidence_pack_v1(tmp_path, monkeypatch):
    root = tmp_path
    monkeypatch.setattr(mod, "ROOT", root)
    monkeypatch.setattr(mod, "OUT", root / "reports" / "external_validation_ms_evidence_pack_v1_latest")
    monkeypatch.setattr(
        mod,
        "MINIMAL_MANIFEST",
        root / "reports/external_validation_minimal_pack_v1_latest/manifest.json",
    )

    payloads = {
        "reports/external_validation_2week_closure_v1_latest.json": {
            "send_gate": "OPEN",
            "ready_for_external_send": True,
            "week2": {"D10": {"readiness_all_ok": False}},
        },
        "reports/external_validation_gate_review_memo_v1_latest.json": {"gate_decision": "OPEN"},
        "docs/final/artifacts/compression_b2b_legal_send_signoff_v1_latest.json": {
            "send_gate": "OPEN",
            "ready_for_external_send": True,
        },
        "reports/external_validation_d6_independent_rehearsal_v1_latest.json": {"status": "ok"},
        "reports/external_validation_briefs_v1_latest/external_validation_tech_brief_v1_latest.json": {},
        "reports/external_validation_briefs_v1_latest/external_validation_tech_brief_v1_latest.md": "# tech\n",
        "reports/external_validation_briefs_v1_latest/external_validation_business_brief_v1_latest.json": {},
        "reports/external_validation_briefs_v1_latest/external_validation_business_brief_v1_latest.md": "# biz\n",
        "reports/customer_compression_stateless_poc_wtt-premium-cs-customer-v1_v1_latest.json": {"ok": True},
        "docs/final/artifacts/compression_b2b_pilot_roi_report_v1_latest.json": {"ok": True},
        "docs/final/artifacts/hybrid_b2b_commercialization_pipeline_v1_latest.json": {"send_gate": "OPEN"},
        "reports/external_validation_minimal_pack_v1_latest/manifest.json": {
            "send_gate": "OPEN",
            "ready_for_external_send": True,
        },
    }
    for rel, payload in payloads.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if rel.endswith(".md"):
            p.write_text(payload, encoding="utf-8")
        else:
            p.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    assert mod.main() == 0
    manifest = json.loads((mod.OUT / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["aux_savings_rate_required"] is False
    assert manifest["send_gate"] == "OPEN"
    assert (mod.OUT / "ms_proposal_headline_links_v1.txt").exists()
