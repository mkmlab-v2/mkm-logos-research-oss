"""Smoke: Track A Phase2 harness scripts (isolated temp artifacts)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


def _py(script: Path, *args: str) -> None:
    subprocess.run([sys.executable, str(script), *args], check=True)


def test_track_a_harness_smoke_isolated(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    meter = tmp_path / "meter.jsonl"
    shutil.copy(root / "tests/fixtures/track_a_metering_log_smoke_v1.jsonl", meter)
    art = tmp_path / "artifacts"
    art.mkdir()

    s_json = art / "track_a_metering_summary_latest.json"
    w_json = art / "track_a_metering_weekly_report_latest.json"
    g_json = art / "track_a_metering_band_gate_latest.json"
    c_json = art / "track_a_conversational_cost_simulation_latest.json"
    e_json = art / "track_a_shadow_corpus_eval_latest.json"
    m_json = art / "track_a_shadow_corpus_input_manifest_latest.json"
    sl = art / "track_a_signal_light_report_latest.json"

    _py(
        root / "scripts/run_track_a_metering_summary.py",
        "--workspace-root",
        str(root),
        "--metering-log",
        str(meter),
        "--out",
        str(s_json),
    )
    d = json.loads(s_json.read_text(encoding="utf-8"))
    assert d.get("schema") == "track_a_metering_summary_v1"
    assert d.get("events_total") == 3

    _py(
        root / "scripts/run_track_a_metering_weekly_report.py",
        "--workspace-root",
        str(root),
        "--metering-log",
        str(meter),
        "--out",
        str(w_json),
    )
    w = json.loads(w_json.read_text(encoding="utf-8"))
    assert w.get("schema") == "track_a_metering_weekly_report_v1"
    assert w.get("events_in_window") == 3

    _py(
        root / "scripts/check_track_a_metering_band_gate.py",
        "--workspace-root",
        str(root),
        "--weekly-json",
        str(w_json),
        "--out",
        str(g_json),
        "--mode",
        "warning",
    )

    _py(
        root / "scripts/run_track_a_conversational_cost_simulation.py",
        "--workspace-root",
        str(root),
        "--out",
        str(c_json),
    )
    c = json.loads(c_json.read_text(encoding="utf-8"))
    assert c.get("schema") == "track_a_conversational_cost_simulation_v1"
    assert c.get("gate_decision") == "GO"

    _py(
        root / "scripts/run_track_a_shadow_corpus_eval.py",
        "--workspace-root",
        str(root),
        "--out-eval",
        str(e_json),
        "--out-manifest",
        str(m_json),
    )
    e = json.loads(e_json.read_text(encoding="utf-8"))
    assert e.get("schema") == "track_a_shadow_corpus_eval_v1"
    assert e.get("status") == "GO"

    _py(
        root / "scripts/build_track_a_signal_light_report.py",
        "--workspace-root",
        str(root),
        "--artifacts-dir",
        str(art),
        "--out",
        str(sl),
    )
    sl_doc = json.loads(sl.read_text(encoding="utf-8"))
    assert sl_doc.get("schema") == "track_a_signal_light_report_v1"
    assert sl_doc.get("signal_light", {}).get("status") == "GREEN"
