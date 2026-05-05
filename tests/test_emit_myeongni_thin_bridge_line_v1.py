# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def mod():
    import importlib.util

    root = Path(__file__).resolve().parents[1]
    scr = root / "scripts" / "emit_myeongni_thin_bridge_line_v1.py"
    spec = importlib.util.spec_from_file_location("emit_myeongni_thin_bridge_line_v1", scr)
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_build_bridge_line_uses_experiment_tail(mod):
    lens = {
        "ts_utc": "2026-01-01T00:00:00Z",
        "scores": {"direction_score": 0.1, "confidence": 0.5},
        "myeongri_stream_outputs": {"state_id": 15, "rationale": "mapping_target=sideways"},
        "provenance": {"input_path": "x"},
    }
    exp_tail = {
        "experiment_id": "exp_test",
        "mapping_target": "bull",
        "vector_4d": {"S": 0.3, "L": 0.2, "K": 0.25, "M": 0.25},
        "state_id": 9,
    }
    row = mod.build_bridge_line(lens=lens, experiment_tail=exp_tail, calendar_date="2023-03-10")
    assert row["ts_utc"].startswith("2023-03-10")
    assert row["mapping_target"] == "bull"
    assert row["state_id"] == 9
    assert row["vector_4d"]["S"] == pytest.approx(0.3)
    assert row["independent_lens_snapshot"]["direction_score"] == 0.1


def test_resolve_calendar_date_auto_nearest(mod, tmp_path):
    cur = tmp_path / "curated_dates_v1.json"
    cur.write_text(
        json.dumps({"dates": ["2022-01-01", "2023-03-10", "2022-06-13"]}),
        encoding="utf-8",
    )
    lens = {"ts_utc": "2026-05-02T00:00:00Z"}
    assert mod.resolve_calendar_date_auto(lens, curated_path=cur) == "2023-03-10"


def test_build_bridge_line_falls_back_to_rationale(mod):
    lens = {
        "scores": {"direction_score": 0.0, "confidence": 0.5},
        "myeongri_stream_outputs": {
            "state_id": 12,
            "rationale": "B-track state_id=12, mapping_target=bear;",
        },
    }
    row = mod.build_bridge_line(lens=lens, experiment_tail=None, calendar_date="2022-06-01")
    assert row["mapping_target"] == "bear"
    assert row["state_id"] == 12


def test_main_writes_jsonl(tmp_path, mod, monkeypatch):
    lens_p = tmp_path / "lens.json"
    exp_p = tmp_path / "exp.jsonl"
    exp_p.write_text(
        json.dumps(
            {
                "experiment_id": "e1",
                "mapping_target": "sideways",
                "vector_4d": {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25},
                "state_id": 4,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    lens_p.write_text(
        json.dumps(
            {
                "scores": {"direction_score": 0.08, "confidence": 0.7},
                "myeongri_stream_outputs": {"state_id": 4},
                "provenance": {"input_path": str(exp_p)},
            }
        ),
        encoding="utf-8",
    )
    out_p = tmp_path / "bridge.jsonl"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "x",
            "--lens-json",
            str(lens_p),
            "--calendar-date",
            "2023-03-10",
            "--out",
            str(out_p),
        ],
    )
    assert mod.main() == 0
    obj = json.loads(out_p.read_text(encoding="utf-8").strip())
    assert obj["ts_utc"].startswith("2023-03-10")
    assert obj["mapping_target"] == "sideways"


def test_main_calendar_date_auto(tmp_path, mod, monkeypatch):
    """Integration: auto resolves to nearest curated grid day."""
    curated = tmp_path / "curated_dates_v1.json"
    curated.write_text(
        json.dumps({"schema": "x", "dates": ["2022-01-01", "2023-03-10"]}),
        encoding="utf-8",
    )
    lens_p = tmp_path / "lens.json"
    lens_p.write_text(
        json.dumps(
            {
                "ts_utc": "2026-05-02T12:00:00Z",
                "scores": {"direction_score": 0.1, "confidence": 0.5},
                "myeongri_stream_outputs": {"state_id": 1, "rationale": "mapping_target=bull"},
            }
        ),
        encoding="utf-8",
    )
    out_p = tmp_path / "bridge.jsonl"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "x",
            "--lens-json",
            str(lens_p),
            "--calendar-date",
            "auto",
            "--curated-dates-json",
            str(curated),
            "--out",
            str(out_p),
        ],
    )
    assert mod.main() == 0
    obj = json.loads(out_p.read_text(encoding="utf-8").strip())
    assert obj["ts_utc"].startswith("2023-03-10")
    assert obj["mapping_target"] == "bull"
