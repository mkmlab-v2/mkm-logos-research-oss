"""Logos Studio query-time BigSet conflict retrieval (Phase 1a)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RETRIEVE = ROOT / "scripts/retrieve_logos_studio_conflict_context_v1.py"
CLIENT = ROOT / "projects/no1kmedi/src/components/logos-research/LogosResearchStudioClient.tsx"
PANEL = ROOT / "projects/no1kmedi/src/components/logos-research/LogosResearchConflictSidecarPanel.tsx"


def _run(query: str, preset_id: str = "") -> dict:
    cmd = [sys.executable, str(RETRIEVE), "--query", query, "--no-embedding"]
    if preset_id:
        cmd.extend(["--preset-id", preset_id])
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout)


def test_nephilim_query_matches_nephilim_group():
    doc = _run("네피림이 뭐야?")
    assert doc["ok"] is True
    assert doc["group_count"] >= 1
    gids = [g["conflict_group_id"] for g in doc["groups"]]
    assert "MKM_CONCEPT_NEPHILIM" in gids


def test_benei_query_matches_sons_of_god():
    doc = _run("하나님의 아들들 Benei HaElohim 창세기 6")
    gids = [g["conflict_group_id"] for g in doc["groups"]]
    assert "MKM_CONCEPT_SONS_OF_GOD" in gids


def test_job_suffering_query_matches_job_group():
    doc = _run("욥기에서 하나님은 왜 욥이 고통받게 하셨는가?", "job_job_suffering_reason")
    assert doc["ok"] is True
    assert doc["group_count"] >= 1
    gids = [g["conflict_group_id"] for g in doc.get("groups") or []]
    assert "MKM_CONCEPT_JOB_SUFFERING" in gids
    assert "MKM_CONCEPT_SONS_OF_GOD" not in gids
    assert "MKM_CONCEPT_NEPHILIM" not in gids


def test_job_suffering_freeform_query():
    doc = _run("욥의 고난의 이유는?")
    gids = [g["conflict_group_id"] for g in doc.get("groups") or []]
    assert "MKM_CONCEPT_JOB_SUFFERING" in gids


def test_preset_boost_nephilim():
    doc = _run("고대 전통", "bigset_topic_nephilim")
    assert doc["match_mode"] == "preset_boost"
    assert doc["groups"][0]["conflict_group_id"] == "MKM_CONCEPT_NEPHILIM"


def test_studio_client_no_static_conflict_mount():
    text = CLIENT.read_text(encoding="utf-8")
    assert "LogosResearchConflictSidecarPanel activePresetId" not in text
    assert "result.conflict_context" in text


def test_conflict_panel_requires_context_prop():
    text = PANEL.read_text(encoding="utf-8")
    assert "activePresetId" not in text
    assert "context:" in text or "context }" in text
    assert "fetch(SIDECAR_URL" not in text
