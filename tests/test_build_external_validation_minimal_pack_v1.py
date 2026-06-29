from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_external_validation_minimal_pack_v1 as mod


def test_build_external_validation_minimal_pack_v1(tmp_path, monkeypatch):
    root = tmp_path
    monkeypatch.setattr(mod, "ROOT", root)
    monkeypatch.setattr(mod, "OUT", root / "reports" / "external_validation_minimal_pack_v1_latest")

    for rel in [
        "docs/final/artifacts/hybrid_b2b_commercialization_pipeline_v1_latest.json",
        "docs/final/artifacts/edge_encoder_spec_v1_latest.json",
        "docs/final/artifacts/compression_b2b_legal_send_signoff_v1_latest.json",
        "reports/hd_autonomous_evolution_completion_v1_latest.json",
        "reports/mkm_high_delegation_preflight_v1_latest.json",
    ]:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if "signoff" in rel:
            p.write_text(
                json.dumps(
                    {
                        "send_gate": "HOLD",
                        "ready_for_external_send": False,
                        "commander_signoff": True,
                        "counsel_signoff": False,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
        else:
            p.write_text('{"ok": true}\n', encoding="utf-8")

    assert mod.main() == 0
    manifest = json.loads((mod.OUT / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["send_gate"] == "HOLD"
    assert len(manifest["bundled_files"]) == 4
