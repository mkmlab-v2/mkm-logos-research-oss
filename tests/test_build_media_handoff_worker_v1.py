"""build_media_handoff_worker_v1 + verify_handoff_closure_v1."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build_media_handoff_worker_v1.py"
CLOSURE = ROOT / "scripts/verify_handoff_closure_v1.py"
FIXTURE = ROOT / "tests/fixtures/media_stt_transcription_v1.example.json"
TRANSCRIPTION_SCHEMA = ROOT / "docs/final/schemas/media_stt_transcription_v1.schema.json"
REPORT_SCHEMA = ROOT / "docs/final/schemas/media_handoff_worker_report_v1.schema.json"


def test_handoff_builder_and_closure(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    task_id = "TEST-UNIT"
    out_dir = tmp_path / "handoff_workers"
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--task-id",
            task_id,
            "--source",
            str(FIXTURE),
            "--out-dir",
            str(out_dir),
            "--strict-schema",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout

    md_path = out_dir / f"HW-{task_id}-LOGOS_CLIP.md"
    report_path = out_dir / f"HW-{task_id}-report.json"
    assert md_path.is_file()
    assert report_path.is_file()

    report = json.loads(report_path.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(json.loads(REPORT_SCHEMA.read_text(encoding="utf-8"))).validate(report)
    assert report["send_gate"] == "HOLD"
    assert len(report["top_segments"]) == 3
    assert report["top_segments"][0]["id"] in {"seg_02", "seg_03"}

    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(json.loads(TRANSCRIPTION_SCHEMA.read_text(encoding="utf-8"))).validate(fixture)

    md_text = md_path.read_text(encoding="utf-8")
    assert "Timeline grid" in md_text or "Timeline" in md_text
    assert "회고" in md_text
    assert "2c. Layer C MDL" in md_text
    assert report.get("layer_c_mdl", {}).get("scholarly_top1")

    close = subprocess.run(
        [
            sys.executable,
            str(CLOSURE),
            "--task-id",
            task_id,
            "--workers-dir",
            str(out_dir),
            "--dry-run",
            "--require-layer-c-mdl",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert close.returncode == 0, close.stderr + close.stdout


def test_fixture_example_top_ranking_order() -> None:
    from scripts.rank_media_segments_v0 import compute_segment_rank_v0

    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    ranked = compute_segment_rank_v0(doc["segments"], doc["theme_keywords"])
    top3_ids = [s["id"] for s in ranked[:3]]
    assert top3_ids[0] in {"seg_02", "seg_03"}
    assert top3_ids[-1] in {"seg_01", "seg_04"}
