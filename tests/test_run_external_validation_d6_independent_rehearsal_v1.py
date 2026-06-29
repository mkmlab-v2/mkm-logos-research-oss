from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_external_validation_d6_independent_rehearsal_v1 as d6_mod


def test_build_report_marks_same_host_dry_run_ok(tmp_path, monkeypatch):
    root = tmp_path
    monkeypatch.setattr(d6_mod, "ROOT", root)
    steps = [
        {"command": "echo 1", "exit_code": 0, "ok": True},
        {"command": "echo 2", "exit_code": 0, "ok": True},
    ]
    gate = {"send_gate": "HOLD", "ready_for_external_send": False, "readiness_all_ok": False}
    for rel in d6_mod.ARTIFACT_CHECKS:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{}\n", encoding="utf-8")

    report = d6_mod.build_report(
        operator="test_operator",
        rehearsal_class="same_host_dry_run",
        commands=["echo 1", "echo 2"],
        steps=steps,
        gate_before=gate,
        gate_after=gate,
    )
    assert report["status"] == "ok"
    assert report["gate_match"] is True
    assert report["summary"]["all_steps_exit_0"] is True
