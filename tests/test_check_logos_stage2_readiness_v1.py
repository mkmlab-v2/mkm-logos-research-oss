from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_logos_stage2_readiness_v1.py"


def test_check_logos_stage2_readiness_passes_latest(tmp_path: Path) -> None:
    out = tmp_path / "stage2.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--ontology-json",
            str(ROOT / "docs" / "final" / "artifacts" / "logos_ontology_registry_v1_latest.json"),
            "--selected-json",
            str(ROOT / "docs" / "final" / "artifacts" / "logos_response_v1_retry_selected_latest.json"),
            "--graph-gate-json",
            str(ROOT / "docs" / "final" / "artifacts" / "public_graph_quality_gate_v1_latest.json"),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_stage2_readiness_v1"
    assert doc["decision"] == "STAGE2_READY"
    assert doc["all_pass"] is True
