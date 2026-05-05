# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_RUNNER = _ROOT / "scripts" / "run_logos_track_b_commander_deep_report_v1.py"


def test_runner_emits_axes_and_gate(tmp_path: Path) -> None:
    logos = tmp_path / "logos.json"
    logos.write_text(
        json.dumps(
            {
                "schema": "logos_independent_lens_v0",
                "version": "0.2.0",
                "scores": {"direction_score": 0.1, "confidence": 0.5},
                "evidence_refs": [{"verse_id": "X.1.1"}, {"verse_id": "Y.2.2"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    out = tmp_path / "rep.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(_RUNNER),
            "--logos",
            str(logos),
            "--no-fusion",
            "--no-market-sasang",
            "--output",
            str(out),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_track_b_commander_deep_report_v1"
    assert doc["human_commander_gate_v1"]["final_authority"] == "human_commander"
    assert "TRACK_B" in (doc.get("labels") or [])
    assert (doc.get("envelope") or {}).get("disclaimer_ko")
    axes = doc.get("report_axes_v1") or {}
    assert "axis_05_lens_conflict_map" in axes
    assert "X.1.1" in str(axes.get("axis_03_cross_reference_echo"))


def test_contract_and_schema_exist() -> None:
    c = _ROOT / "docs" / "final" / "artifacts" / "LOGOS_TRACK_B_COMMANDER_DEEP_REPORT_V1_CONTRACT.json"
    s = _ROOT / "docs" / "final" / "schemas" / "logos_track_b_commander_deep_report_v1.schema.json"
    assert c.is_file() and s.is_file()


def test_materialize_writes_md(tmp_path: Path) -> None:
    env = _ROOT / "data" / "logos" / "logos_track_b_commander_deep_report_envelope_v1.json"
    assert env.is_file()
    rep = tmp_path / "r.json"
    rep.write_text(
        json.dumps(
            {
                "schema": "logos_track_b_commander_deep_report_v1",
                "version": "1.1.0",
                "ts_utc": "2026-01-01T00:00:00Z",
                "hypothesis_tier": "B",
                "boundary_ack": True,
                "a_track_autotrigger_forbidden": True,
                "labels": ["TRACK_B", "HYPO"],
                "human_commander_gate_v1": {
                    "schema": "human_commander_gate_v1",
                    "version": "1.0.0",
                    "track": "B",
                    "banner_ko": "[TRACK B]",
                    "final_authority": "human_commander",
                    "machine_output_role": "decision_support_observation_only",
                },
                "envelope": {"disclaimer_ko": "테스트 면책"},
                "machine_role_ko": "역할",
                "report_axes_v1": {
                    "axis_01_original_language_semantics": {
                        "title_ko": "축1",
                        "deterministic_stub_ko": "내용",
                    }
                },
                "inputs_digest": {},
                "note": "x",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    out_md = tmp_path / "out.md"
    mat = _ROOT / "scripts" / "materialize_logos_track_b_commander_deep_report_v1.py"
    cp = subprocess.run(
        [sys.executable, str(mat), "--input", str(rep), "--output", str(out_md)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert cp.returncode == 0, cp.stderr
    body = out_md.read_text(encoding="utf-8")
    assert "축1" in body and "테스트 면책" in body
