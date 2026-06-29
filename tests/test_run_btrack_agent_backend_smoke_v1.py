"""B-track agent backend smoke — dry-run contract [HYPO]."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_btrack_agent_backend_smoke_dry_run() -> None:
    out = ROOT / "reports/tmp_btrack_agent_backend_smoke_v1_test.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_btrack_agent_backend_smoke_v1.py"),
            "--dry-run",
            "--backends",
            "ollama,cloud",
            "--max-cases",
            "3",
            "--out-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "btrack_agent_backend_smoke_v1"
    assert doc.get("research_only") is True
    assert len(doc.get("backends") or []) == 2
    ollama = doc["backends"][0]
    assert ollama["dry_run"] is True
    assert ollama["fixture_count"] == 3


def test_btrack_agent_backend_smoke_fixtures_file() -> None:
    path = ROOT / "data/btrack/agent_backend_smoke_fixtures_v1.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc.get("schema") == "btrack_agent_backend_smoke_fixtures_v1"
    assert len(doc.get("fixtures") or []) >= 3
