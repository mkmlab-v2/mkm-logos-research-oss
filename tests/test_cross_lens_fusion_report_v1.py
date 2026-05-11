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
    assert rep["va_snapshot"]["cooldown_applied"] is False
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


def test_fusion_report_includes_cooldown_flags():
    from scripts.build_cross_lens_fusion_report_v1 import build_report

    stub = ROOT / "tests/fixtures/cross_lens_fusion_candidates_sample_v1.json"
    va_doc = {
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
        "status": "COOLDOWN_ACTIVE",
        "cooldown_control": {
            "policy_id": "va_cooldown_control_v1",
            "enabled": True,
            "applied": True,
            "reasons": ["high_arousal"],
            "before_va": {"valence": -0.2, "arousal": 0.95},
            "after_va": {"valence": -0.2, "arousal": 0.75},
            "thresholds": {
                "high_arousal_cut": 0.9,
                "low_valence_cut": -0.9,
                "arousal_decay_step": 0.2,
                "valence_recovery_step": 0.15,
            },
        },
    }
    rep = build_report(va_doc, stub)
    assert rep["va_snapshot"]["cooldown_applied"] is True
    assert rep["va_snapshot"]["cooldown_policy_id"] == "va_cooldown_control_v1"
    assert rep["va_snapshot"]["cooldown_reasons"] == ["high_arousal"]


def test_high_arousal_cooldown_damps_joy_energy_multiplier():
    from scripts.build_cross_lens_fusion_report_v1 import COOLDOWN_JOY_ENERGY_DAMP_HIGH_AROUSAL, build_report

    stub = ROOT / "tests/fixtures/cross_lens_fusion_candidates_sample_v1.json"
    base_va = {
        "schema": "va_trajectory_log_v1",
        "session_id": "t",
        "turn_index": 0,
        "timestamp_utc": "2026-05-11T00:00:00Z",
        "parameters": {"ema_alpha": 0.3},
        "trajectory": {
            "previous_va": {"valence": 0.0, "arousal": 0.0},
            "target_va": {"valence": 0.0, "arousal": 0.0},
            "current_va": {"valence": 0.5, "arousal": 0.1},
        },
        "status": "TRACKING_ACTIVE",
    }
    rep_plain = build_report(base_va, stub)
    joy_plain = next(x for x in rep_plain["candidates_ranked"] if x["verse_id"] == "STUB.JOY.02")
    assert joy_plain["fusion_multiplier_pre_damp"] == pytest.approx(1.08, abs=1e-9)
    assert joy_plain["cooldown_damp_factor"] == 1.0
    assert joy_plain["fusion_multiplier"] == pytest.approx(1.08, abs=1e-9)

    va_cool = {
        **base_va,
        "status": "COOLDOWN_ACTIVE",
        "cooldown_control": {
            "policy_id": "va_cooldown_control_v1",
            "enabled": True,
            "applied": True,
            "reasons": ["high_arousal"],
            "before_va": {"valence": 0.5, "arousal": 0.95},
            "after_va": {"valence": 0.5, "arousal": 0.1},
            "thresholds": {
                "high_arousal_cut": 0.9,
                "low_valence_cut": -0.9,
                "arousal_decay_step": 0.2,
                "valence_recovery_step": 0.15,
            },
        },
    }
    rep_cool = build_report(va_cool, stub)
    joy_cool = next(x for x in rep_cool["candidates_ranked"] if x["verse_id"] == "STUB.JOY.02")
    assert joy_cool["cooldown_fusion_damp_applied"] is True
    assert joy_cool["cooldown_damp_factor"] == pytest.approx(COOLDOWN_JOY_ENERGY_DAMP_HIGH_AROUSAL, abs=1e-9)
    assert joy_cool["cooldown_damp_rules_applied"] == ["high_arousal_joy_energy_damp"]
    assert joy_cool["fusion_multiplier"] == pytest.approx(1.08 * COOLDOWN_JOY_ENERGY_DAMP_HIGH_AROUSAL, abs=1e-9)
    assert joy_cool["fusion_weight"] < joy_plain["fusion_weight"]


def test_low_valence_cooldown_damps_caution_temperance_multiplier():
    from scripts.build_cross_lens_fusion_report_v1 import COOLDOWN_CAUTION_TEMPERANCE_DAMP_LOW_VALENCE, build_report

    stub = ROOT / "tests/fixtures/cross_lens_fusion_candidates_sample_v1.json"
    base_va = {
        "schema": "va_trajectory_log_v1",
        "session_id": "t",
        "turn_index": 0,
        "timestamp_utc": "2026-05-11T00:00:00Z",
        "parameters": {"ema_alpha": 0.3},
        "trajectory": {
            "previous_va": {"valence": 0.0, "arousal": 0.0},
            "target_va": {"valence": 0.0, "arousal": 0.0},
            "current_va": {"valence": -0.2, "arousal": 0.6},
        },
        "status": "TRACKING_ACTIVE",
    }
    rep_plain = build_report(base_va, stub)
    caution_plain = next(x for x in rep_plain["candidates_ranked"] if x["verse_id"] == "STUB.CAUTION.03")
    assert caution_plain["fusion_multiplier_pre_damp"] == pytest.approx(1.12, abs=1e-9)
    assert caution_plain["cooldown_damp_factor"] == 1.0

    va_cool = {
        **base_va,
        "status": "COOLDOWN_ACTIVE",
        "cooldown_control": {
            "policy_id": "va_cooldown_control_v1",
            "enabled": True,
            "applied": True,
            "reasons": ["low_valence"],
            "before_va": {"valence": -0.95, "arousal": 0.6},
            "after_va": {"valence": -0.2, "arousal": 0.6},
            "thresholds": {
                "high_arousal_cut": 0.9,
                "low_valence_cut": -0.9,
                "arousal_decay_step": 0.2,
                "valence_recovery_step": 0.15,
            },
        },
    }
    rep_cool = build_report(va_cool, stub)
    caution_cool = next(x for x in rep_cool["candidates_ranked"] if x["verse_id"] == "STUB.CAUTION.03")
    assert caution_cool["cooldown_fusion_damp_applied"] is True
    assert caution_cool["cooldown_damp_factor"] == pytest.approx(COOLDOWN_CAUTION_TEMPERANCE_DAMP_LOW_VALENCE, abs=1e-9)
    assert caution_cool["cooldown_damp_rules_applied"] == ["low_valence_caution_temperance_damp"]
    assert caution_cool["fusion_multiplier"] == pytest.approx(
        caution_plain["fusion_multiplier_pre_damp"] * COOLDOWN_CAUTION_TEMPERANCE_DAMP_LOW_VALENCE,
        abs=1e-9,
    )


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

