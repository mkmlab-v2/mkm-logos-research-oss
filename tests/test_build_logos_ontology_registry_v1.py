from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_logos_ontology_registry_v1.py"
VALIDATE = ROOT / "scripts" / "validate_logos_ontology_v1.py"


def test_build_logos_ontology_registry_and_validate(tmp_path: Path) -> None:
    out = tmp_path / "logos_ontology_registry_v1.json"
    cp = subprocess.run(
        [sys.executable, str(BUILD), "--output-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_ontology_mapping_v1"
    assert doc["guardrails"]["non_gating_only"] is True
    assert doc["guardrails"]["price_mapping_forbidden"] is True
    assert doc["guardrails"]["execution_trigger_allowed"] is False
    assert len(doc["relations"]) >= 4
    roots = doc["entities"]["morphology_roots"]
    assert any(r.get("verification_status") == "verified" for r in roots)

    vp = subprocess.run(
        [sys.executable, str(VALIDATE), "validate", "--input", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert vp.returncode == 0, vp.stderr + vp.stdout
