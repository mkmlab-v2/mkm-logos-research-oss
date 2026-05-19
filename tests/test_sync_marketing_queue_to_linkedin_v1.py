"""sync_marketing_queue_to_linkedin_v1 — unified queue -> linkedin queue."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/sync_marketing_queue_to_linkedin_v1.py"
EXAMPLE = ROOT / "data/marketing/marketing_content_queue_v1.example.json"
SCHEMA = ROOT / "docs/final/schemas/marketing_content_queue_v1.schema.json"


def test_example_validates_against_schema():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    doc = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)


def test_sync_linkedin_items(tmp_path):
    unified = tmp_path / "marketing_content_queue.json"
    unified.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    linkedin = tmp_path / "linkedin_queue.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--unified-queue",
            str(unified),
            "--linkedin-queue",
            str(linkedin),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(linkedin.read_text(encoding="utf-8"))
    assert out["schema"] == "linkedin_b2b_queue_v1"
    assert len(out["items"]) == 2
    assert all(i["id"] for i in out["items"])


def test_pull_linkedin_status_to_unified(tmp_path):
    unified = tmp_path / "marketing_content_queue.json"
    unified.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    linkedin = tmp_path / "linkedin_queue.json"
    subprocess.run(
        [sys.executable, str(SCRIPT), "--unified-queue", str(unified), "--linkedin-queue", str(linkedin)],
        cwd=str(ROOT),
        check=True,
    )
    li = json.loads(linkedin.read_text(encoding="utf-8"))
    li["items"][0]["status"] = "drafted"
    li["items"][0]["drafted_at_utc"] = "2026-05-19T00:00:00Z"
    li["items"][0]["draft_paths"] = {"markdown": "reports/foo_[DRAFT].md"}
    linkedin.write_text(json.dumps(li, indent=2), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--unified-queue",
            str(unified),
            "--linkedin-queue",
            str(linkedin),
            "--pull-linkedin-status",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    u = json.loads(unified.read_text(encoding="utf-8"))
    first = next(i for i in u["items"] if i["id"] == li["items"][0]["id"])
    assert first["status"] == "drafted"
    assert first["draft_paths"]["markdown"] == "reports/foo_[DRAFT].md"
