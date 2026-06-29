"""LocalLock vault audit smoke — Windows-only, no secret values."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts/check_local_lock_vault_audit_v1.py"
OUT = ROOT / "reports/local_lock_vault_audit_v1_latest.json"


@pytest.mark.skipif(sys.platform != "win32", reason="Vault audit is Windows DPAPI scoped")
def test_vault_audit_runs_and_writes_report():
    proc = subprocess.run(
        [sys.executable, str(AUDIT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert OUT.is_file(), proc.stderr
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc.get("schema") == "local_lock_vault_audit_v1"
    assert "local_lock" in doc
    assert "api_infra_secret_keys" in doc
    assert proc.returncode in (0, 1)
