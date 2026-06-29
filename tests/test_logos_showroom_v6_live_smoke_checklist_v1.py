# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts/check_logos_showroom_v6_live_smoke_checklist_v1.py"


def test_live_smoke_checklist_skip_network_exit0() -> None:
    cp = subprocess.run(
        [sys.executable, str(CHECKER), "--skip-network"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    out = ROOT / "reports/logos_showroom_v6_live_smoke_checklist_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("gate_pass") is True
    assert doc.get("checks", {}).get("network_skipped") is True


def test_live_smoke_remote_optional() -> None:
    """Live HTTP to api.jemaai.cloud — informational; skip-network is CI default."""
    cp = subprocess.run(
        [sys.executable, str(CHECKER)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    doc_path = ROOT / "reports/logos_showroom_v6_live_smoke_checklist_v1_latest.json"
    if not doc_path.is_file():
        pytest.skip("no smoke report")
    doc = json.loads(doc_path.read_text(encoding="utf-8"))
    if cp.returncode != 0:
        failures = doc.get("gate_failures") or []
        if failures and all(
            any(tok in f.lower() for tok in ("fetch", "unreachable", "timeout", "urlerror"))
            for f in failures
        ):
            pytest.skip(f"live smoke skipped: {failures}")
    assert cp.returncode == 0, cp.stderr or cp.stdout
