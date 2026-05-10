from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _write_chain(path: Path, *, peak: float, rms: float, status: str, notes: list[str], seconds: float) -> None:
    doc = {
        "schema": "lens_music_gate_chain_v1",
        "melody_stage_m13": {
            "schema": "melody_audition_wav_v1",
            "peak_abs_0_1": peak,
            "rms_0_1": rms,
            "seconds": seconds,
            "sanity_m14": {
                "status": status,
                "notes": notes,
                "non_blocking": True,
            },
        },
    }
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_build_audition_qa_summary_from_chain_jsons(tmp_path):
    c1 = tmp_path / "chain_ok.json"
    c2 = tmp_path / "chain_warn.json"
    _write_chain(c1, peak=0.24, rms=0.11, status="OK", notes=[], seconds=8.0)
    _write_chain(c2, peak=0.97, rms=0.005, status="WARN", notes=["peak_near_clipping"], seconds=7.5)

    out = tmp_path / "summary.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_lens_music_audition_qa_summary_v1.py"),
            "--chain-json",
            str(c1),
            "--chain-json",
            str(c2),
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    summary = json.loads(out.read_text(encoding="utf-8"))
    assert summary["schema"] == "lens_music_audition_qa_summary_v1"
    assert summary["parsed_chain_count"] == 2
    assert summary["audition_stage_count"] == 2
    assert summary["sanity_status_counts"]["OK"] == 1
    assert summary["sanity_status_counts"]["WARN"] == 1
    assert summary["sanity_note_counts"]["peak_near_clipping"] == 1
    assert summary["metrics"]["peak_abs_max"] >= 0.97
    assert summary["metrics"]["warn_ratio"] == 0.5
    assert summary["governance_m16"]["state"] == "WATCH"


def test_build_audition_qa_summary_go_state_with_relaxed_threshold(tmp_path):
    c1 = tmp_path / "chain_ok.json"
    c2 = tmp_path / "chain_warn.json"
    _write_chain(c1, peak=0.24, rms=0.11, status="OK", notes=[], seconds=8.0)
    _write_chain(c2, peak=0.97, rms=0.005, status="WARN", notes=["peak_near_clipping"], seconds=7.5)

    out = tmp_path / "summary_go.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_lens_music_audition_qa_summary_v1.py"),
            "--chain-json",
            str(c1),
            "--chain-json",
            str(c2),
            "--warn-ratio-threshold",
            "0.8",
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    summary = json.loads(out.read_text(encoding="utf-8"))
    assert summary["governance_m16"]["state"] == "GO"


def test_build_audition_qa_summary_fails_without_inputs():
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_lens_music_audition_qa_summary_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 2
