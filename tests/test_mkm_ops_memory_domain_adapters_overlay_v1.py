"""Tests for domain adapter ops_memory overlay + sync_bridge gate ([HYPO])."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from mkm_ops_memory_index_lib_v1 import (  # noqa: E402
    build_domain_adapter_overlay_nodes,
    merge_overlay_nodes,
    nodes_for_resume,
    resolve_lane_from_topic,
)

OVERLAY = ROOT / "scripts" / "build_mkm_ops_memory_domain_adapters_overlay_v1.py"
GATE = ROOT / "scripts" / "check_mkm_ops_sync_bridge_domain_adapters_v1.py"
BRIDGE = ROOT / "docs/final/artifacts/mkm_ops_sync_bridge_v1.json"


def test_resolve_lane_pixel_and_audio_topics() -> None:
    assert resolve_lane_from_topic("pixel battalion sprite mkmlife") == "design"
    assert resolve_lane_from_topic("lens audio bgm musicgen") == "design"


def test_build_domain_adapter_overlay_nodes(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    reports.mkdir(parents=True)
    (reports / "mkmlife_pixel_sprite_urls_gate_v1_latest.json").write_text(
        json.dumps(
            {
                "overall_ok": True,
                "ok_count": 3,
                "fail_count": 0,
                "track_wall": "B-track UI asset gate — not Track A",
                "hypothesis_tag": "[HYPO]",
                "lane": "research_only",
            }
        ),
        encoding="utf-8",
    )
    (reports / "audio_gate_latest.json").write_text(
        json.dumps(
            {
                "decision": "PASS",
                "track": "B",
                "metrics": {
                    "lens_alignment_pass": True,
                    "bpm_target": 102.0,
                },
                "provenance": {"commercial_terms_tag": "apache2_self_host_weights_v1"},
            }
        ),
        encoding="utf-8",
    )
    nodes = build_domain_adapter_overlay_nodes(tmp_path)
    assert "prism_ops_pixel_battalion_gate" in nodes
    assert "prism_ops_lens_audio_gate" in nodes


def test_merge_domain_adapter_into_design_lane(tmp_path: Path) -> None:
    base = {
        "schema": "mkm_ops_memory_index_v1",
        "nodes": {
            "prism_ops_mission_log_board": {"priority": 10},
            "prism_ops_central_checkpoint": {"priority": 9},
            "prism_ops_lane_design": {"priority": 7},
            "prism_ops_pixel_battalion_gate": {"priority": 6, "field_tags": ["pixel"]},
            "prism_ops_lens_audio_gate": {"priority": 6, "field_tags": ["audio"]},
        },
    }
    merged = merge_overlay_nodes(
        base,
        {"prism_ops_pixel_battalion_gate": base["nodes"]["prism_ops_pixel_battalion_gate"]},
        overlay_label="domain_adapters_v1",
    )
    lane_ids = [nid for nid, _ in nodes_for_resume(merged, lane="design")]
    assert "prism_ops_pixel_battalion_gate" in lane_ids
    assert "prism_ops_lens_audio_gate" in lane_ids


def test_sync_bridge_domain_adapters_gate_live() -> None:
    cp = subprocess.run(
        [sys.executable, str(GATE)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    doc = json.loads((ROOT / "reports/mkm_ops_sync_bridge_domain_adapters_gate_v1_latest.json").read_text())
    assert doc["ok"] is True
    assert doc["adapter_count"] == 2


def test_bridge_has_domain_adapters_section() -> None:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8-sig"))
    section = bridge.get("domain_adapters") or {}
    ids = [a.get("id") for a in section.get("adapters") or []]
    assert "pixel_battalion" in ids
    assert "lens_audio" in ids


def test_overlay_cli_merges_into_index(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    reports.mkdir(parents=True)
    (reports / "mkmlife_pixel_sprite_urls_gate_v1_latest.json").write_text(
        json.dumps(
            {
                "overall_ok": True,
                "ok_count": 1,
                "fail_count": 0,
                "track_wall": "B-track UI",
                "hypothesis_tag": "[HYPO]",
                "lane": "research_only",
            }
        ),
        encoding="utf-8",
    )
    (reports / "audio_gate_latest.json").write_text(
        json.dumps(
            {
                "decision": "PASS",
                "track": "B",
                "metrics": {"lens_alignment_pass": True},
                "provenance": {"commercial_terms_tag": "apache2_self_host_weights_v1"},
            }
        ),
        encoding="utf-8",
    )
    index_path = tmp_path / "storage" / "meta" / "index.json"
    index_path.parent.mkdir(parents=True)
    index_path.write_text(
        json.dumps({"schema": "mkm_ops_memory_index_v1", "nodes": {}}),
        encoding="utf-8",
    )
    cp = subprocess.run(
        [
            sys.executable,
            str(OVERLAY),
            "--workspace-root",
            str(tmp_path),
            "--index",
            str(index_path),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr
    loaded = json.loads(index_path.read_text(encoding="utf-8"))
    assert "prism_ops_pixel_battalion_gate" in loaded["nodes"]
    assert "domain_adapters_v1" in loaded.get("overlays", [])
