"""Smoke tests for postit_pointer v0 schema + validator."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_postit_pointer_v1.py"
SCHEMA = ROOT / "docs/final/schemas/postit_pointer_v1.schema.json"
FIXTURE = ROOT / "docs/final/artifacts/fixtures/postit_pointer_v1.example.json"


def _run_validator(*extra: str) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(SCRIPT), "--stdout-only", *extra]
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)


def test_fixture_passes_validator() -> None:
    proc = _run_validator()
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads(proc.stdout)
    assert report["schema"] == "postit_pointer_validation_v1"
    assert report["ok"] is True
    assert report["denominators"]["schema"] == "postit_pointer_denominators_v1"
    assert "zone_g_health" in report["denominators"]["zone_shards"]


def test_myeongri_eval_script_has_zone_pointer() -> None:
    path = ROOT / "scripts" / "run_myeongri_deterministic_lora_inference_eval_v1.py"
    text = path.read_text(encoding="utf-8-sig")
    assert "postit_v2:" in text
    assert '"pointer"' in text
    assert "zone_d_ssot" in text


@pytest.mark.skipif(
    not SCHEMA.exists() or not FIXTURE.exists(),
    reason="schema or fixture missing",
)
def test_schema_matches_fixture() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)


def test_invalid_zone_id_fails(tmp_path: Path) -> None:
    bad = tmp_path / "bad_pointer.json"
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    doc["pointer"] = {"zone_id": "zone_not_a_real_shard"}
    bad.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    proc = _run_validator("--json", str(bad), "--skip-v2")
    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert report["ok"] is False
    assert any("zone_id not in codebook" in f["error"] for f in report["failures"])
