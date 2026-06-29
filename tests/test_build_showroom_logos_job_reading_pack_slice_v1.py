# Keywords: build_showroom_logos_job_reading_pack_slice_v1, showroom, NON_GATING, export guard

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/build_showroom_logos_job_reading_pack_slice_v1.py"
SCHEMA = ROOT / "docs/final/schemas/showroom_logos_job_reading_pack_slice_v1.schema.json"
TOPOLOGY = ROOT / "docs/final/artifacts/logos_topology_sidecar_job_suffering_reason_v1_latest.json"
VERIFY_CHAIN = ROOT / "reports/logos_job_reading_pack_verify_chain_v1_latest.json"
GUARD = ROOT / "scripts/showroom_public_export_guard_v1.py"


def test_paths_exist() -> None:
    assert RUNNER.is_file()
    assert SCHEMA.is_file()
    assert TOPOLOGY.is_file()


def test_build_slice_with_verify_gate(tmp_path: Path) -> None:
    if not VERIFY_CHAIN.is_file():
        subprocess.run(
            [sys.executable, "scripts/run_logos_job_reading_pack_verify_chain_v1.py"],
            cwd=str(ROOT),
            check=True,
            capture_output=True,
            text=True,
        )
    out = tmp_path / "slice.json"
    r = subprocess.run(
        [sys.executable, str(RUNNER), "--out-json", str(out), "--no-mirror-artifact"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema_version"] == "showroom_logos_job_reading_pack_slice_v1"
    assert doc["send_gate"] == "HOLD"
    assert doc["why_question_assembled"] is False
    assert doc["disclaimer"]["gating_status"] == "NON_GATING"
    assert len(doc["reading_packs"]) == 3
    assert doc["export_gate"]["reading_pack_verify_ok"] is True
    for pack in doc["reading_packs"]:
        assert len(pack["card_excerpt_ko"]) >= 20
        assert "docs/research/" not in pack["card_excerpt_ko"]


def test_build_slice_json_schema(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    out = tmp_path / "slice2.json"
    subprocess.run(
        [sys.executable, str(RUNNER), "--out-json", str(out), "--no-mirror-artifact"],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    doc = json.loads(out.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)


def test_export_guard_no_forbidden_keys(tmp_path: Path) -> None:
    sys.path.insert(0, str(ROOT))
    from scripts.showroom_public_export_guard_v1 import scan_forbidden

    out = tmp_path / "slice3.json"
    subprocess.run(
        [sys.executable, str(RUNNER), "--out-json", str(out), "--no-mirror-artifact"],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    doc = json.loads(out.read_text(encoding="utf-8"))
    violations = scan_forbidden(doc)
    assert violations == [], violations

    bad = dict(doc)
    bad["vector_4d"] = {"S": 0.25}
    assert scan_forbidden(bad)
