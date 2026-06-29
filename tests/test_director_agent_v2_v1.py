from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
SCRIPT = ROOT / "scripts/cinematic/director_agent_v2.py"
SHOT_PLAN = ART / "director_agent_v2_shot_plan_latest.json"
SCENARIO = ART / "cinematic_scenario_v2_ko.txt"


def test_director_agent_v2_builds_shot_plan():
    r = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert SHOT_PLAN.is_file()

    doc = json.loads(SHOT_PLAN.read_text(encoding="utf-8"))
    assert doc["schema"] == "director_agent_v2_shot_plan"
    assert doc["target_shots"] == 8
    assert doc["shot_sec"] == 5
    assert doc["fact_lock"]["send_gate"] == "HOLD"
    anchors = doc["fact_lock"].get("external_benchmark_anchors") or []
    assert len(anchors) >= 1
    assert anchors[0].get("anchor_id") == "deepmind_a24_previz"
    assert anchors[0].get("overclaim_guard") == "O-02"

    shots = doc["shots"]
    assert len(shots) == 8

    anchor_ids = {a["anchor_id"] for a in [
        {"anchor_id": "dawn_witness"},
        {"anchor_id": "purify_daily"},
        {"anchor_id": "observe_field"},
        {"anchor_id": "base_lock"},
        {"anchor_id": "rest_gate"},
        {"anchor_id": "noise_filter"},
        {"anchor_id": "manifest_commit"},
        {"anchor_id": "final_sync"},
    ]}

    for shot in shots:
        assert shot.get("narration_ko")
        assert shot.get("graph_anchor", {}).get("anchor_id")
        prompt = shot.get("prompt_motion_en", "")
        assert prompt
        for aid in anchor_ids:
            assert aid not in prompt.lower(), f"{aid} leaked into prompt for {shot['shot_id']}"
        assert "dialogue" not in prompt.lower() or "no dialogue" in prompt.lower()
        assert shot.get("negative_nouns")
        assert shot.get("flow_mode_hint") in ("fast_iterate", "quality_final")

    assert shots[-1]["flow_mode_hint"] == "quality_final"
    assert SCENARIO.is_file()


def test_cinematic_v2_workspace_bootstrap():
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/cinematic/bootstrap_cinematic_v2_workspace_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert r.returncode == 0, r.stderr + r.stdout
    bootstrap = ART / "cinematic_v2_workspace_bootstrap_latest.json"
    doc = json.loads(bootstrap.read_text(encoding="utf-8"))
    assert doc["schema"] == "cinematic_v2_workspace_bootstrap_v1"
    assert doc["shot_count"] == 8
    refs = ART / "cinematic_v2_workspace" / "references" / "README_REF_IMAGES.txt"
    assert refs.is_file()


def test_cinematic_v2_shot01_narration_render():
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/cinematic/bootstrap_cinematic_v2_workspace_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        check=True,
    )
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/cinematic/render_cinematic_v2_narration_edge_tts_v1.py"),
            "--shot-id",
            "SHOT_01",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if r.returncode != 0 and "edge-tts" in (r.stdout + r.stderr):
        pytest.skip("edge-tts not installed")
    assert r.returncode == 0, r.stderr + r.stdout
    render_doc = json.loads((ART / "cinematic_v2_narration_render_latest.json").read_text(encoding="utf-8"))
    assert render_doc.get("ok") is True
    wav = ART / "cinematic_v2_workspace" / "shots" / "shot_01" / "narration.wav"
    assert wav.is_file()
    assert wav.stat().st_size > 1000


def test_cinematic_v2_shot01_flow_handoff():
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/cinematic/bootstrap_cinematic_v2_workspace_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        check=True,
    )
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/cinematic/build_cinematic_v2_shot01_flow_handoff_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert r.returncode == 0, r.stderr + r.stdout
    handoff = ART / "cinematic_v2_shot01_flow_handoff_latest.json"
    doc = json.loads(handoff.read_text(encoding="utf-8"))
    assert doc["schema"] == "cinematic_v2_shot01_flow_handoff_v1"
    assert doc["shot_id"] == "SHOT_01"
    assert doc.get("prompt_motion_en")
    assert doc.get("send_gate") == "HOLD"
    assert (ART / "cinematic_v2_shot01_flow_handoff_latest.txt").is_file()
