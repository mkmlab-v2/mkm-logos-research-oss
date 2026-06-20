"""Reproduce bundle for Hybrid Memory OS shallow stack."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/ollama_shallow_hybrid_reproduce_bundle_v1_latest.json"


def test_hybrid_reproduce_bundle_skip_ollama_exit0() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_ollama_shallow_hybrid_reproduce_bundle_v1.py"),
            "--skip-ollama",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc.get("schema") == "ollama_shallow_hybrid_reproduce_bundle_v1"
    assert doc.get("send_gate") == "HOLD"
    assert doc.get("ok") is True
    assert doc.get("steps", {}).get("pytest_offline", {}).get("ok") is True
    assert doc.get("steps", {}).get("e2e_dry_run", {}).get("ok") is True
