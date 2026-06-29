"""Smoke tests for concept_bridge Human Gate queue builder."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build_logos_concept_bridge_human_gate_queue_v1.py"
REGISTRY = ROOT / "docs/final/artifacts/logos_concept_bridge_registry_v1_latest.json"


def test_build_queue_smoke(tmp_path: Path) -> None:
    assert REGISTRY.is_file()
    out = tmp_path / "queue.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--registry",
            str(REGISTRY),
            "--out",
            str(out),
            "--wave",
            "1",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_concept_bridge_human_gate_queue_v1"
    assert doc["research_only"] is True
    assert doc["send_gate"] == "HOLD"
    assert doc["wave"] == 1
    assert doc["hypothesis_class"] == "HYPO"
    assert isinstance(doc["entries"], list)
    for entry in doc["entries"]:
        assert entry["status"] == "human_gate_pending"
        assert entry["signoff_marker_present"] is False
        assert entry["wave"] == 1


def test_build_queue_detects_unsigned_bridge(tmp_path: Path) -> None:
    reg = json.loads(REGISTRY.read_text(encoding="utf-8-sig"))
    fixture_reg = tmp_path / "registry_unsigned_fixture.json"
    signed_entry = next(
        e for e in reg.get("entries") or [] if isinstance(e, dict) and e.get("present")
    )
    artifact_src = ROOT / str(signed_entry["artifact_path"])
    artifact_dst = tmp_path / "unsigned_bridge_fixture.json"
    artifact_doc = json.loads(artifact_src.read_text(encoding="utf-8-sig"))
    policy = artifact_doc.get("policy") if isinstance(artifact_doc.get("policy"), dict) else {}
    policy.pop("human_signoff_completed", None)
    policy.pop("human_reviewed", None)
    policy.pop("human_signoff_utc", None)
    policy.pop("human_signoff_by", None)
    policy.pop("signoff_lane", None)
    artifact_doc["policy"] = policy
    artifact_dst.write_text(json.dumps(artifact_doc, ensure_ascii=False, indent=2), encoding="utf-8")

    unsigned_entry = dict(signed_entry)
    unsigned_entry["concept_id"] = "concept:fixture_unsigned_bridge"
    unsigned_entry["artifact_path"] = str(artifact_dst)
    unsigned_entry["human_reviewed"] = False
    fixture_doc = {
        **{k: v for k, v in reg.items() if k != "entries"},
        "entries": [unsigned_entry],
        "human_reviewed_count": 0,
        "human_reviewed_ratio": 0.0,
    }
    fixture_reg.write_text(json.dumps(fixture_doc, ensure_ascii=False, indent=2), encoding="utf-8")

    out = tmp_path / "queue2.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--registry",
            str(fixture_reg),
            "--out",
            str(out),
            "--wave",
            "1",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["queue_count"] == 1
    assert doc["entries"][0]["concept_id"] == "concept:fixture_unsigned_bridge"
    assert doc["entries"][0]["status"] == "human_gate_pending"
