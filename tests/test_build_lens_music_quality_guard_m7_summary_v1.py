from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _write_chain(path: Path, status: str, check_rows: list[dict]) -> None:
    doc = {
        "schema": "lens_music_gate_chain_v1",
        "quality_guard_m7": {
            "enabled": True,
            "status": status,
            "warn_count": sum(1 for c in check_rows if c.get("status") == "WARN"),
            "checks": check_rows,
        },
    }
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_build_m7_summary_from_chain_jsons(tmp_path):
    c1 = tmp_path / "chain_ok.json"
    c2 = tmp_path / "chain_warn.json"
    _write_chain(
        c1,
        "OK",
        [
            {"id": "tempo_drift_cap_12bpm", "status": "OK"},
            {"id": "velocity_within_safety_cap", "status": "OK"},
        ],
    )
    _write_chain(
        c2,
        "WARN",
        [
            {"id": "tempo_drift_cap_12bpm", "status": "WARN"},
            {"id": "velocity_within_safety_cap", "status": "OK"},
        ],
    )

    out = tmp_path / "summary.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_lens_music_quality_guard_m7_summary_v1.py"),
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
    assert summary["schema"] == "lens_music_quality_guard_m7_summary_v1"
    assert summary["parsed_chain_count"] == 2
    assert summary["guard_status_counts"]["OK"] == 1
    assert summary["guard_status_counts"]["WARN"] == 1
    assert summary["checks_rollup"]["tempo_drift_cap_12bpm"]["status_counts"]["WARN"] == 1


def test_build_m7_summary_fails_without_inputs():
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_lens_music_quality_guard_m7_summary_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 2
