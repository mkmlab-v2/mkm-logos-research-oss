"""Build logos_chronology_v1 from repo SSOT and validate against schema."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None  # type: ignore[assignment]


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_build_logos_chronology_from_repo_ssot_validates(tmp_path: Path) -> None:
    out = tmp_path / "logos_chronology_v1_latest.json"
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_logos_chronology_from_repo_ssot_v1.py"), "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    schema = json.loads((ROOT / "docs/final/schemas/logos_chronology_v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)
    assert len(doc["eras"]) >= 4
    assert len(doc["modern_bridges"]) >= 5
    assert doc["hypothesis_tier"] == "[HYPO]"
