"""Smoke: Theographic entity edge ingest (fixture sample)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/ingest_logos_theographic_entity_edges_v1.py"


def test_ingest_fixture_sample():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "theo_edges.jsonl"
        report = Path(tmp) / "report.json"
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--use-fixture-sample",
                "--out-jsonl",
                str(out),
                "--report",
                str(report),
                "--min-edges",
                "3",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert proc.returncode == 0, proc.stderr or proc.stdout
        lines = [json.loads(x) for x in out.read_text(encoding="utf-8").splitlines() if x.strip()]
        assert len(lines) >= 3
        assert all(row.get("source") == "theographic" for row in lines)
        assert any(row.get("entity_kind") == "person" for row in lines)
        doc = json.loads(report.read_text(encoding="utf-8"))
        assert doc["schema"] == "logos_theographic_entity_ingest_v1"
        assert doc["send_gate"] == "HOLD"


def test_license_gate_requires_ack():
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--theographic-dir",
            str(ROOT / "storage/external_kg/theographic_v1"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode != 0
    assert "ack-license" in (proc.stderr or proc.stdout).lower()
