"""Azure OpenAI synthesis on DE probe — dry-run contract."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts/run_ng40_de_probe_azure_openai_synthesis_v1.py"
PROBE = ROOT / "reports/ng40_de_logos_anchor_probe_v1_latest.json"


def test_dry_run_schema() -> None:
    out = ROOT / "reports/_test_de_probe_azure_synthesis_v1.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--probe-json",
            str(PROBE),
            "--out-json",
            str(out),
            "--max-probes",
            "2",
            "--dry-run",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "ng40_de_probe_azure_openai_synthesis_v1"
    assert doc["billing_surface"] == "azure_openai"
    assert len(doc["syntheses"]) == 2
    assert doc["syntheses"][0]["status"] == "dry_run_skipped"
