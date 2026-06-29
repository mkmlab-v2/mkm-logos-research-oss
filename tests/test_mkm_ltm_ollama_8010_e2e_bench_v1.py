"""E2E LTM × Ollama × 8010 bench — dry-run smoke only (no live services required)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/mkm_ltm_ollama_8010_e2e_bench_v1_latest.json"


def test_e2e_bench_dry_run_exit0() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_mkm_ltm_ollama_8010_e2e_bench_v1.py"),
            "--dry-run",
            "--out-json",
            str(ROOT / "reports/mkm_ltm_ollama_8010_e2e_bench_v1_dryrun_test.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(
        (ROOT / "reports/mkm_ltm_ollama_8010_e2e_bench_v1_dryrun_test.json").read_text(encoding="utf-8")
    )
    assert doc.get("schema") == "mkm_ltm_ollama_8010_e2e_bench_v1"
    assert doc.get("mode") == "dry_run"
    assert len(doc.get("rows") or []) == 8
    assert doc.get("send_gate") == "HOLD"


def test_e2e_bench_report_schema_keys_when_present() -> None:
    if not OUT.is_file():
        return
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc.get("schema") == "mkm_ltm_ollama_8010_e2e_bench_v1"
    assert "component_headlines_separate" in doc
    assert "raw" in doc
    assert "repair_v2" in doc
