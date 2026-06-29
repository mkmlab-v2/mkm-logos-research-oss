# Keywords: research_shadow_lane, hypothesis_tree, NON_GATING, job_prologue

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/build_research_shadow_lane_hypothesis_tree_v1.py"
CHAIN = ROOT / "scripts/run_hypo_generation_chain_v1.ps1"
SCHEMA = ROOT / "docs/final/schemas/research_shadow_lane_hypothesis_tree_v1.schema.json"
SEED = ROOT / "docs/final/artifacts/research_shadow_lane_seeds/job_prologue_suffering_v1.json"


def test_paths_exist() -> None:
    assert RUNNER.is_file()
    assert SCHEMA.is_file()
    assert SEED.is_file()


def test_build_hypothesis_tree(tmp_path: Path) -> None:
    out = tmp_path / "tree.json"
    r = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--seed-json",
            str(SEED),
            "--out-json",
            str(out),
            "--out-artifact",
            str(tmp_path / "art.json"),
            "--skip-validate",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema_version"] == "research_shadow_lane_hypothesis_tree_v1"
    assert doc["disclaimer"]["gating_status"] == "NON_GATING"
    assert doc["rail_status"]["send_gate"] == "HOLD"
    assert doc["rail_status"]["verified_anchor_achieved"] is False
    assert len(doc["hypotheses"]) >= 5
    for h in doc["hypotheses"]:
        assert h["status"] == "path_only_not_verdict"
        assert h["tags"]["canon"] in ("green", "yellow", "red")


def test_build_hypothesis_tree_schema(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    out = tmp_path / "tree2.json"
    subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--seed-json",
            str(SEED),
            "--out-json",
            str(out),
            "--out-artifact",
            str(tmp_path / "art2.json"),
        ],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    doc = json.loads(out.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)
