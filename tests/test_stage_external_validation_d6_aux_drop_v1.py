from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import stage_external_validation_d6_aux_drop_v1 as stage_mod


def test_stage_external_validation_d6_aux_drop_v1(tmp_path, monkeypatch):
    root = tmp_path / "ws"
    share = tmp_path / "share"
    monkeypatch.setattr(stage_mod, "ROOT", root)
    monkeypatch.setattr(stage_mod, "OUT", root / "reports/external_validation_d6_aux_drop_v1_latest.json")
    monkeypatch.setattr(
        stage_mod,
        "MANIFEST_SRC",
        root / "reports/external_validation_minimal_pack_v1_latest/manifest.json",
    )
    monkeypatch.setattr(stage_mod, "RUNNER_SRC", root / "scripts/run_external_validation_d6_aux_runner_v1.py")
    monkeypatch.setattr(
        stage_mod,
        "PROMPT_SRC",
        root / "scripts/assets/external_validation_d6_aux_cursor_prompt_v1.txt",
    )

    manifest = {"reproduce_week1": ["echo ok"], "gate_baseline": {"send_gate": "HOLD"}}
    for rel, content in {
        "reports/external_validation_minimal_pack_v1_latest/manifest.json": manifest,
        "scripts/run_external_validation_d6_aux_runner_v1.py": "# runner\n",
        "scripts/assets/external_validation_d6_aux_cursor_prompt_v1.txt": "prompt\n",
    }.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if rel.endswith(".json"):
            p.write_text(json.dumps(content) + "\n", encoding="utf-8")
        else:
            p.write_text(content, encoding="utf-8")

    doc = stage_mod.stage(share, r"C:\workspace")
    assert doc["ok"] is True
    assert (share / "RUN_D6_ON_AUX.cmd").exists()
    assert (share / "d6_job_request_v1.json").exists()
