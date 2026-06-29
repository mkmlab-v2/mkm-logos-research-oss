"""Offline smoke: deployment axis isolation probe structure."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "scripts/probe_mkm_deployment_axis_isolation_v1.py"
CHAIN = ROOT / "scripts/run_mkm_deployment_axis_isolation_chain_v1.py"


def test_probe_script_axes_and_checks():
    text = PROBE.read_text(encoding="utf-8")
    assert "mkm_deployment_axis_isolation_probe_v1" in text
    assert '"axis": "mkmlife_cf"' in text
    assert '"axis": "jema_logos_dns"' in text
    assert "mkmlife_data_internal_blocked" in text
    assert "jema_app_logos_research_canonical_redirect" in text
    assert "expect_location_contains" in text
    assert "no_redirect" in text


def test_chain_wrapper_exists():
    text = CHAIN.read_text(encoding="utf-8")
    assert "probe_mkm_deployment_axis_isolation_v1.py" in text
    assert "mkm_deployment_axis_isolation_chain_v1" in text


def test_scheduler_tier4_ssot_registered():
    stack_path = ROOT / "docs/final/artifacts/mkm_scheduler_solo_core_stack_v1.json"
    import json

    stack = json.loads(stack_path.read_text(encoding="utf-8-sig"))
    tier4 = stack.get("tier4_solo_intentional_keep") or []
    assert "\\MKM_Deployment_Axis_Isolation_Weekly" in tier4
