"""Re-invention guard — Logos theory→implementation wiring registry."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/final/artifacts/logos_theory_implementation_wiring_v1.json"
CHECK = ROOT / "scripts/check_logos_theory_implementation_wiring_v1.py"
SANDBOX_BRIDGE = ROOT / "scripts/core/gematria_to_4d_bridge_sandbox_v1.py"
RESUME_BUILDER = ROOT / "scripts/build_mkm_chat_resume_pack_v1.py"


def test_wiring_registry_check_exit0() -> None:
    proc = subprocess.run(
        [sys.executable, str(CHECK), "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    report = json.loads(proc.stdout)
    assert report["ok"] is True
    assert report["edge_count"] >= 7


def test_spread_dynamic_tuning_edge_in_registry() -> None:
    doc = json.loads(REGISTRY.read_text(encoding="utf-8"))
    dynamic = next(
        (e for e in doc["canonical_edges"] if e["edge_id"] == "spread_dynamic_tuning"),
        None,
    )
    assert dynamic is not None
    assert (ROOT / dynamic["implementation_scripts"][0]).is_file()
    assert (ROOT / dynamic["ui_wire"][0]).is_file()


def test_sandbox_edge_forbids_dynamic_override_alias() -> None:
    doc = json.loads(REGISTRY.read_text(encoding="utf-8"))
    sandbox = next(e for e in doc["canonical_edges"] if e["edge_id"] == "spread_sandbox_research")
    aliases = set(sandbox.get("forbidden_aliases") or [])
    assert "bridge_v1_dynamic_override" in aliases
    assert (ROOT / sandbox["implementation_scripts"][0]).is_file()


def test_resume_pack_builder_references_wiring_registry() -> None:
    text = RESUME_BUILDER.read_text(encoding="utf-8")
    assert "logos_theory_implementation_wiring_v1" in text


def test_sandbox_bridge_recipe_id_stable() -> None:
    text = SANDBOX_BRIDGE.read_text(encoding="utf-8")
    assert 'RECIPE_ID = "gematria_bridge_sandbox_v1"' in text
