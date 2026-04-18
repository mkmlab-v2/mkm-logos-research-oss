"""Regression: stress UAV bench input → hybrid bench preserves critical-field wire integrity."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
STRESS_INPUT = ROOT / "docs" / "final" / "artifacts" / "defense_uav_bench_stress_v0.json"


def test_stress_input_file_exists() -> None:
    assert STRESS_INPUT.is_file(), f"missing {STRESS_INPUT}"


def test_hybrid_bench_merged_primary_plus_stress(tmp_path: Path) -> None:
    """108 records: default 100 + stress 8; does not overwrite committed defense_hybrid_compression_bench_v0.json."""
    out = tmp_path / "merged_bench.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_defense_hybrid_compression_bench.py"),
            "--append-stress",
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("aggregate", {}).get("critical_field_integrity") == 1.0
    assert doc.get("record_count") == 108
    assert doc.get("stress_input_appended") == "docs/final/artifacts/defense_uav_bench_stress_v0.json"


def test_hybrid_bench_stress_critical_integrity(tmp_path: Path) -> None:
    out = tmp_path / "defense_hybrid_compression_bench_stress_v0.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_defense_hybrid_compression_bench.py"),
            "--input",
            str(STRESS_INPUT),
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    agg = doc.get("aggregate") or {}
    assert agg.get("critical_field_integrity") == 1.0
    assert doc.get("record_count") == 8
    assert len(doc.get("per_record") or []) == 8
    for row in doc.get("per_record") or []:
        assert row.get("critical_round_trip_ok") is True


def test_code_pack_forbidden_scan_clean() -> None:
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "defense_code_pack_v1.py"), "--scan-text", "UAV 합성 벤치는 연구용이며 MoD 인증이 아닙니다."],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr


def test_code_pack_forbidden_scan_detects_substring() -> None:
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "defense_code_pack_v1.py"), "--scan-text", "통신 단절 시 완벽 복원을 보장합니다."],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 3
    assert "FORBIDDEN_HITS" in (r.stdout or "")
