"""Cloud resilience concept bridge (LLM plan materialize)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build_logos_concept_bridge_cloud_resilience_poc_v1.py"
SCHEMA = ROOT / "docs/final/schemas/logos_concept_bridge_v1.schema.json"


def test_cloud_resilience_bridge_schema(tmp_path: Path) -> None:
    out = tmp_path / "bridge.json"
    cp = subprocess.run(
        [sys.executable, str(BUILDER), "--output-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_concept_bridge_v1"
    assert doc["policy"]["generation_method"] == "llm_plan_template_v1"
    assert doc["policy"]["llm_api_called"] is False
    assert len(doc["paths"]) >= 3
    jsonschema = __import__("jsonschema")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)
