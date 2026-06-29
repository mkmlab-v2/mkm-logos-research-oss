"""PersonaDiary Logos sidebar human rubric pilot v1."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(
    __import__("importlib").util.find_spec("jsonschema") is None,
    reason="jsonschema not installed",
)
def test_personadiary_logos_sidebar_human_rubric_schema_and_gates() -> None:
    import jsonschema

    out = ROOT / "docs/final/artifacts/personadiary_logos_sidebar_human_rubric_v1_latest.json"
    if not out.is_file():
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/build_personadiary_logos_sidebar_human_rubric_v1.py"),
                "--strict",
            ],
            cwd=str(ROOT),
            timeout=90,
        )
        assert proc.returncode == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    schema = json.loads(
        (
            ROOT / "docs/final/schemas/personadiary_logos_sidebar_human_rubric_v1.schema.json"
        ).read_text(encoding="utf-8")
    )
    jsonschema.validate(instance=doc, schema=schema)
    assert doc.get("prophecy_vote") == "none"
    assert doc.get("send_gate") == "HOLD"
    assert doc.get("track_a_blocked") is True
    assert doc.get("ok") is True
    summary = doc.get("summary") or {}
    assert summary.get("n_queries", 0) >= 5
    assert summary.get("structural_pass_rate", 0) >= 0.8
    assert summary.get("human_rubric_mean") is None
    for row in doc.get("rows") or []:
        assert len(row.get("hits") or []) == 3
        assert (row.get("structural") or {}).get("structural_pass") is True
