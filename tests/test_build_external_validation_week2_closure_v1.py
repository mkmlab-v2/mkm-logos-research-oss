from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_external_validation_week2_closure_v1 as mod


def test_build_external_validation_week2_closure_v1(tmp_path, monkeypatch):
    root = tmp_path
    monkeypatch.setattr(mod, "ROOT", root)
    monkeypatch.setattr(mod, "ART", root / "docs" / "final" / "artifacts")
    monkeypatch.setattr(mod, "REPORTS", root / "reports")
    monkeypatch.setattr(mod, "OUT_DIR", root / "reports" / "external_validation_briefs_v1_latest")
    monkeypatch.setattr(mod, "CLOSURE", root / "reports" / "external_validation_2week_closure_v1_latest.json")
    monkeypatch.setattr(
        mod,
        "LEGAL_SIGNOFF",
        root / "docs" / "final" / "artifacts" / "compression_b2b_legal_send_signoff_v1_latest.json",
    )

    hybrid = {
        "send_gate": "HOLD",
        "ready_for_external_send": False,
    }
    for rel, payload in {
        "docs/final/artifacts/compression_b2b_legal_send_signoff_v1_latest.json": {
            "commander_signoff": True,
            "counsel_signoff": False,
            "send_gate": "HOLD",
            "ready_for_external_send": False,
        },
        "docs/final/artifacts/hybrid_b2b_commercialization_pipeline_v1_latest.json": hybrid,
        "docs/final/artifacts/hybrid_b2b_commercialization_pipeline_v1_latest.md": "# ok\nFAIL-COMP-004\n",
        "docs/final/artifacts/edge_encoder_vpc_deploy_runbook_v1_latest.json": {"ok": True},
        "reports/external_validation_minimal_pack_v1_latest/manifest.json": {
            "reproduce_week1": ["py echo"],
            "gate_baseline": {"send_gate": "HOLD"},
        },
        "reports/demo/edge_encoder_vpc_deploy_checklist_v1.html": "<html></html>",
        "reports/external_validation_d6_independent_rehearsal_v1_latest.json": {
            "status": "ok",
            "rehearsal_class": "same_host_dry_run",
            "gate_match": True,
            "summary": {"all_steps_exit_0": True},
            "reproduce": "py scripts/run_external_validation_d6_independent_rehearsal_v1.py",
        },
    }.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if rel.endswith(".html"):
            p.write_text(payload, encoding="utf-8")
        else:
            p.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    assert mod.main() == 0
    closure = json.loads(mod.CLOSURE.read_text(encoding="utf-8"))
    assert closure["send_gate"] == "HOLD"
    assert closure["week2"]["D6"]["status"] == "ok"
    assert closure["human_blockers"] == ["legal_ops_signoff"]
