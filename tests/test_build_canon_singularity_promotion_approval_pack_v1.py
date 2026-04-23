from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_build_canon_singularity_promotion_approval_pack_v1(tmp_path: Path):
    go = tmp_path / "go.json"
    rehearsal = tmp_path / "rehearsal.json"
    runbook = tmp_path / "runbook.json"
    freeze = tmp_path / "freeze.json"
    diff = tmp_path / "diff.json"
    out_json = tmp_path / "pack.json"
    out_md = tmp_path / "pack.md"
    go.write_text(json.dumps({"verdict": "go", "hold_reasons": []}), encoding="utf-8")
    rehearsal.write_text(json.dumps({"ops_alert_summary": {"ops_alert": False, "severity": "none"}}), encoding="utf-8")
    runbook.write_text(json.dumps({"ops_alert_summary": {"ops_alert": False, "severity": "none"}}), encoding="utf-8")
    freeze.write_text(json.dumps({"freeze_decision": "frozen"}), encoding="utf-8")
    diff.write_text(json.dumps({"total_change_count": 3}), encoding="utf-8")
    cmd = [
        sys.executable,
        "scripts/core/build_canon_singularity_promotion_approval_pack_v1.py",
        "--go-no-go-json",
        str(go),
        "--rehearsal-latest-json",
        str(rehearsal),
        "--ops-alert-runbook-json",
        str(runbook),
        "--freeze-vfinal-json",
        str(freeze),
        "--freeze-generation-diff-json",
        str(diff),
        "--output-json",
        str(out_json),
        "--output-md",
        str(out_md),
    ]
    cp = subprocess.run(cmd, check=False, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert cp.returncode == 0
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["schema"] == "original_corpus_regime_singularity_canon_promotion_approval_pack_v1"
    assert data["verdict"] == "approved"
    assert out_md.exists()

