from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _write_chain(path: Path, *, status: str, peak: float, rms: float) -> None:
    doc = {
        "schema": "lens_music_gate_chain_v1",
        "melody_stage_m13": {
            "schema": "melody_audition_wav_v1",
            "peak_abs_0_1": peak,
            "rms_0_1": rms,
            "seconds": 8.0,
            "sanity_m14": {"status": status, "notes": [], "non_blocking": True},
        },
    }
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_governance_chain_builds_status_from_summary(tmp_path):
    c1 = tmp_path / "chain1.json"
    c2 = tmp_path / "chain2.json"
    _write_chain(c1, status="OK", peak=0.2, rms=0.1)
    _write_chain(c2, status="WARN", peak=0.98, rms=0.005)
    summary = tmp_path / "summary.json"
    status_out = tmp_path / "status.json"

    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_lens_music_audition_governance_chain_v1.py"),
            "--chain-glob",
            str(tmp_path / "chain*.json"),
            "--warn-ratio-threshold",
            "0.2",
            "--summary-out",
            str(summary),
            "--status-out",
            str(status_out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    status = json.loads(status_out.read_text(encoding="utf-8"))
    assert status["schema"] == "lens_music_audition_governance_status_v1"
    assert status["state"] == "WATCH"
    assert status["advisory_only"] is True
