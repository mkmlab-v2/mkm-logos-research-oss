# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts/check_mkm_marketing_ip_governance_v1.py"
CHARTER = ROOT / "docs/final/artifacts/mkm_marketing_ip_governance_charter_draft_v1.json"


def test_marketing_ip_charter_has_blocklist() -> None:
    assert CHARTER.is_file()
    doc = json.loads(CHARTER.read_text(encoding="utf-8"))
    assert doc["schema"] == "mkm_marketing_ip_governance_charter_draft_v1"
    assert "internal_term_blocklist_public" in doc
    assert "금화교역" in doc["internal_term_blocklist_public"]


def test_marketing_ip_governance_gate_exit0() -> None:
    cp = subprocess.run(
        [sys.executable, str(CHECKER)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
