from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_cross_lens_fusion_example_validates_against_schema():
    jsonschema = pytest.importorskip("jsonschema")
    schema_path = ROOT / "docs/final/schemas/cross_lens_fusion_report_v1.schema.json"
    example_path = ROOT / "docs/final/schemas/cross_lens_fusion_report_v1.example.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    instance = json.loads(example_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=instance, schema=schema)


def test_fusion_rank_changes_with_va_snapshot():
    from scripts.build_cross_lens_fusion_report_v1 import build_report

    stub = ROOT / "tests/fixtures/cross_lens_fusion_candidates_sample_v1.json"
    va_low = {
        "schema": "va_trajectory_log_v1",
        "session_id": "t",
        "turn_index": 0,
        "timestamp_utc": "2026-05-11T00:00:00Z",
        "parameters": {"ema_alpha": 0.3},
        "trajectory": {
            "previous_va": {"valence": 0.0, "arousal": 0.0},
            "target_va": {"valence": 0.0, "arousal": 0.0},
            "current_va": {"valence": -0.2, "arousal": 0.75},
        },
        "status": "TRACKING_ACTIVE",
    }
    rep = build_report(va_low, stub)
    ranked = rep["candidates_ranked"]
    assert ranked[0]["verse_id"] == "STUB.PEACE.01"
    joy = next(x for x in ranked if x["verse_id"] == "STUB.JOY.02")
    assert joy["rank_before"] == 1 and joy["rank_after"] == 2

    va_high_v = {
        **va_low,
        "trajectory": {
            **va_low["trajectory"],
            "current_va": {"valence": 0.5, "arousal": 0.1},
        },
    }
    rep2 = build_report(va_high_v, stub)
    top2 = rep2["candidates_ranked"][0]["verse_id"]
    assert top2 == "STUB.JOY.02"


def test_cli_writes_valid_schema(tmp_path: Path):
    jsonschema = pytest.importorskip("jsonschema")
    va_path = tmp_path / "va.json"
    va_path.write_text(
        json.dumps(
            {
                "schema": "va_trajectory_log_v1",
                "session_id": "cli",
                "turn_index": 0,
                "timestamp_utc": "2026-05-11T00:00:00Z",
                "parameters": {"ema_alpha": 0.3},
                "trajectory": {
                    "previous_va": {"valence": 0.0, "arousal": 0.0},
                    "target_va": {"valence": 0.0, "arousal": 0.0},
                    "current_va": {"valence": -0.2, "arousal": 0.75},
                },
                "status": "TRACKING_ACTIVE",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    out = tmp_path / "fusion.json"
    schema = json.loads(
        (ROOT / "docs/final/schemas/cross_lens_fusion_report_v1.schema.json").read_text(encoding="utf-8")
    )
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_cross_lens_fusion_report_v1.py"),
            "--va-trajectory-json",
            str(va_path),
            "--candidates-stub-json",
            str(ROOT / "tests/fixtures/cross_lens_fusion_candidates_sample_v1.json"),
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    doc = json.loads(out.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)
