"""Smoke: Gnosis KG lemma edge ingest (fixture sample, no merge)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/ingest_logos_gnosis_kg_lemma_edges_v1.py"
FIXTURE = ROOT / "tests/fixtures/gnosis_kg_sample_v1"


def test_ingest_fixture_sample_no_merge():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "gnosis_edges.jsonl"
        report = Path(tmp) / "report.json"
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--use-fixture-sample",
                "--no-merge",
                "--out-jsonl",
                str(out),
                "--report",
                str(report),
                "--min-edges",
                "5",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert proc.returncode == 0, proc.stderr or proc.stdout
        assert out.is_file()
        lines = [json.loads(x) for x in out.read_text(encoding="utf-8").splitlines() if x.strip()]
        assert len(lines) >= 5
        assert all(row.get("edge_type") == "GNOSIS_STRONGS_CONTAIN" for row in lines)
        assert all(row.get("source") == "gnosis_kg" for row in lines)
        doc = json.loads(report.read_text(encoding="utf-8"))
        assert doc["schema"] == "logos_gnosis_kg_ingest_v1"
        assert doc["send_gate"] == "HOLD"


def test_license_gate_requires_ack():
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--gnosis-dir",
            str(FIXTURE),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode != 0
    assert "ack-license" in (proc.stderr or proc.stdout).lower()
