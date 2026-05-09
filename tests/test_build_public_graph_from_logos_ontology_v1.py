from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_public_graph_from_logos_ontology_v1.py"


def test_build_public_graph_from_ontology_smoke(tmp_path: Path) -> None:
    out = tmp_path / "public_graph_response_v1_latest.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--ontology-json",
            str(ROOT / "docs" / "final" / "artifacts" / "logos_ontology_registry_v1_latest.json"),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "public_graph_response_v1"
    assert doc["policy_label"] == "NON_GATING"
    assert doc["research_only"] is True
    assert doc["no_trading_advice"] is True
    assert isinstance(doc["nodes"], list)
    assert isinstance(doc["edges"], list)
    assert isinstance(doc["insights"], list)
    assert len(doc["nodes"]) >= 1
    assert len(doc["insights"]) >= 1
