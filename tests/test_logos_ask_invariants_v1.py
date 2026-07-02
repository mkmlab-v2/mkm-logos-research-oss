"""Logos Ask invariants v1 — static + display smoke."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_check_logos_ask_invariants_exit_0():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_logos_ask_invariants_v1.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_quality_completion_contract_fixture():
    import json

    path = ROOT / "docs/final/fixtures/logos_ask_quality_completion_contract_v1.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert len(doc.get("completion_rules_ko") or []) == 5
    assert len(doc.get("live_battery_queries") or []) >= 5
    assert doc.get("live_battery_prod_base") == "https://logos.jema-ai.com"


def test_live_battery_default_base_and_probe_surface():
    sys.path.insert(0, str(ROOT / "scripts"))
    from run_logos_ask_live_battery_v1 import (  # noqa: WPS433
        live_battery_probe_surface,
        load_live_battery_prod_base,
    )

    assert load_live_battery_prod_base() == "https://logos.jema-ai.com"
    assert live_battery_probe_surface("https://logos.jema-ai.com") == "production"
    assert live_battery_probe_surface("https://jema-ai.com") == "production_apex_no_api"
    assert live_battery_probe_surface("http://127.0.0.1:3010") == "localhost_staging"
