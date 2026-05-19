"""generate_linkedin_b2b_copy_v1 — queue validation and assemble-only path."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/generate_linkedin_b2b_copy_v1.py"
EXAMPLE = ROOT / "data/marketing/linkedin_queue_v1.example.json"
SCHEMA = ROOT / "docs/final/schemas/linkedin_b2b_queue_v1.schema.json"


def test_schema_and_example_queue_validate():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    doc = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)
    assert doc["schema"] == "linkedin_b2b_queue_v1"
    assert len(doc["items"]) >= 1


def test_dry_run_example_queue(tmp_path):
    q = tmp_path / "queue.json"
    q.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--queue", str(q), "--dry-run"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "queue ok" in proc.stdout


def test_assemble_only_writes_draft(tmp_path):
    q = tmp_path / "queue.json"
    doc = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    doc["items"] = [doc["items"][0]]
    doc["items"][0]["status"] = "pending"
    q.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    out_dir = tmp_path / "drafts"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--queue",
            str(q),
            "--assemble-only",
            "--item-id",
            doc["items"][0]["id"],
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env={**__import__("os").environ, "MKM_LINKEDIN_DRAFT_ROOT": str(out_dir)},
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "[DRAFT]" in proc.stdout or "drafted:" in proc.stdout
    updated = json.loads(q.read_text(encoding="utf-8"))
    assert updated["items"][0]["status"] == "drafted"
    rel_md = updated["items"][0]["draft_paths"]["markdown"]
    assert (ROOT / rel_md).is_file()
    text = (ROOT / rel_md).read_text(encoding="utf-8")
    assert "[DRAFT]" in text
    assert "guaranteed returns" not in text.lower() or "BANNED" in text
