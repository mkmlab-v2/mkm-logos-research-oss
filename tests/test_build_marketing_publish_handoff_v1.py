"""build_marketing_publish_handoff_v1 + set_marketing_queue_publish_status_v1."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HANDOFF = ROOT / "scripts/build_marketing_publish_handoff_v1.py"
STATUS = ROOT / "scripts/set_marketing_queue_publish_status_v1.py"
EXAMPLE = ROOT / "data/marketing/marketing_content_queue_v1.example.json"
SCHEMA = ROOT / "docs/final/schemas/marketing_publish_handoff_v1.schema.json"


def test_handoff_schema_validates_example_structure(tmp_path):
    jsonschema = pytest.importorskip("jsonschema")
    unified = tmp_path / "q.json"
    unified.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    draft_dir = tmp_path / "drafts"
    draft_dir.mkdir()
    (draft_dir / "compression_governance_moat_w12_2026-05-19_[DRAFT].md").write_text(
        "# [DRAFT]\n\nTest body.\n",
        encoding="utf-8",
    )
    out_json = tmp_path / "handoff.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(HANDOFF),
            "--unified-queue",
            str(unified),
            "--out-json",
            str(out_json),
            "--skip-md",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env={**dict(__import__("os").environ), "PYTHONPATH": str(ROOT / "scripts")},
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(out_json.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(out)
    assert out["auto_publish_allowed"] is False


def test_approve_and_publish_flow(tmp_path):
    unified = tmp_path / "marketing_content_queue.json"
    linkedin = tmp_path / "linkedin_queue.json"
    doc = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    doc["items"][0]["status"] = "drafted"
    doc["items"][0]["draft_paths"] = {"markdown": "reports/foo_[DRAFT].md"}
    unified.write_text(json.dumps(doc, indent=2), encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            str(STATUS),
            "--unified-queue",
            str(unified),
            "--linkedin-queue",
            str(linkedin),
            "--item-id",
            "compression_governance_moat_w12",
            "--approve",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    u = json.loads(unified.read_text(encoding="utf-8"))
    assert u["items"][0]["status"] == "human_approved"
    assert linkedin.is_file()
