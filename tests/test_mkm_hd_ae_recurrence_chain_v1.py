"""HD AE recurrence chain runner tests."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
RUNNER = ROOT / "scripts" / "run_mkm_hd_ae_recurrence_chain_v1.py"


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run([PY, str(RUNNER), *args], cwd=str(ROOT), capture_output=True, text=True, check=False)


def test_chain_runs_with_profile_defaults():
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "chain.json"
        proc = _run(["--out", str(out)])
        assert proc.returncode == 0, proc.stdout + proc.stderr
        doc = json.loads(out.read_text(encoding="utf-8"))
        assert doc["ok"] is True
        assert doc["window_days"] >= 1
        assert doc["repeat_threshold"] >= 1
        assert doc["catalog_rule_count"] is not None
        assert doc["enforced_count"] is not None
        assert isinstance(doc["catalog_sha256"], str) and len(doc["catalog_sha256"]) == 64


def test_chain_override_window_and_threshold():
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "chain.json"
        proc = _run(["--window-days", "14", "--repeat-threshold", "3", "--out", str(out)])
        assert proc.returncode == 0, proc.stdout + proc.stderr
        doc = json.loads(out.read_text(encoding="utf-8"))
        assert doc["window_days"] == 14
        assert doc["repeat_threshold"] == 3
        assert doc["denominator_registry_path"].endswith("mkm_hd_ae_named_defect_catalog_v1.json")
