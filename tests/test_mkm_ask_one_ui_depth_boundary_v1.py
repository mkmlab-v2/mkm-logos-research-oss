"""Ask One UI depth boundary v1 — oracle-sphere vs ask-one product ladder."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/final/artifacts/mkm_ask_one_ui_depth_boundary_v1_latest.json"
PUBLIC = ROOT / "projects/mkm/mkm-life/public/data/mkm_ask_one_ui_depth_boundary_v1.json"
LIB = ROOT / "projects/mkm/mkm-life/lib/mkm-ask-one-ui-depth-boundary-v1.ts"
PANEL = ROOT / "projects/mkm/mkm-life/components/magic-orb/ProductDepthContrastPanel.tsx"
BUILD = ROOT / "scripts/build_mkm_ask_one_ui_depth_boundary_v1.py"
CHECK = ROOT / "scripts/check_mkmlife_design_kernel_v1.py"


def test_depth_boundary_artifact_schema() -> None:
    assert ARTIFACT.is_file()
    doc = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert doc["schema"] == "mkm_ask_one_ui_depth_boundary_v1"
    assert doc["send_gate_default"] == "HOLD"
    assert doc["track_a_blocked"] is True
    assert len(doc["feature_rows"]) >= 5
    delta = set(doc["visual_contract"]["highlight_delta_ids"])
    row_ids = {r["id"] for r in doc["feature_rows"]}
    assert delta.issubset(row_ids)


def test_public_json_synced_with_artifact() -> None:
    assert PUBLIC.is_file()
    art = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    pub = json.loads(PUBLIC.read_text(encoding="utf-8"))
    assert art["schema"] == pub["schema"]
    assert art["feature_rows"] == pub["feature_rows"]


def test_ts_lib_and_panel_wired() -> None:
    lib = LIB.read_text(encoding="utf-8")
    assert "UI_DEPTH_BOUNDARY" in lib
    assert "mkm_ask_one_ui_depth_boundary_v1.json" in lib
    panel = PANEL.read_text(encoding="utf-8")
    assert "ProductDepthContrastPanel" in panel
    assert "oracle_cta" in panel
    assert "ask_one_hero" in panel


def test_build_script_exit_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(BUILD)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_check_mkmlife_design_kernel_includes_depth_boundary() -> None:
    proc = subprocess.run(
        [sys.executable, str(CHECK)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    out = json.loads(proc.stdout.strip())
    assert out["overall_ok"] is True
    assert out.get("depth_boundary_ok") is True
