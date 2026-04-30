from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_layer1_layer5_governance_readiness_v1.py"


def test_governance_readiness_ready(tmp_path: Path) -> None:
    integrated = tmp_path / "integrated.json"
    goldset = tmp_path / "goldset.json"
    out = tmp_path / "out.json"
    integrated.write_text(json.dumps({"decision": "GO_CONTROLLED"}), encoding="utf-8")
    goldset.write_text(json.dumps({"approved_count": 50, "source_mode": "approved_only"}), encoding="utf-8")

    proc = subprocess.run(
        [
            "py",
            str(SCRIPT),
            "--integrated-json",
            str(integrated),
            "--goldset-summary-json",
            str(goldset),
            "--output-json",
            str(out),
            "--require-decision",
            "GO_CONTROLLED",
            "--min-approved-count",
            "50",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["status"] == "READY"
