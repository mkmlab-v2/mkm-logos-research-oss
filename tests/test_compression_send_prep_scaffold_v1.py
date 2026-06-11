"""SEND prep scaffold — stub JSONL row count + intake kit contract."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUB = ROOT / "data/compression/pilot_masked_customer_stub_v1.example.jsonl"
KIT = ROOT / "docs/final/artifacts/compression_pilot_target_intake_kit_v1_latest.json"


def test_stub_jsonl_min_cases() -> None:
    lines = [ln for ln in STUB.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) >= 20
    first = json.loads(lines[0])
    assert "text" in first
    assert "masked" in first.get("labels", []) or "[masked]" in first["text"]


def test_intake_kit_send_hold() -> None:
    doc = json.loads(KIT.read_text(encoding="utf-8"))
    assert doc.get("send_gate") == "HOLD"
    assert doc.get("ready_for_external_send") is False
    assert doc.get("corpus_requirements", {}).get("min_cases", 0) >= 20


def test_send_prep_scaffold_validate_only() -> None:
    for shell in ("pwsh", "powershell"):
        proc = subprocess.run(
            [
                shell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                "scripts/Invoke-CompressionSendPrepScaffold_v1.ps1",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            return
    assert proc.returncode == 0, proc.stderr or proc.stdout
