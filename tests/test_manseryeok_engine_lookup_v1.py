"""Engine-only manseryeok lookup API smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_lookup_from_request_cohort_ganji():
    from scripts.manseryeok_engine_lookup_v1 import lookup_from_request

    body = {
        "schema": "saju_global_birth_request_v1",
        "version": "1.0.0",
        "birth_instant_utc": "1992-03-12T17:00:00Z",
        "iana_tz": "Asia/Seoul",
    }
    out = lookup_from_request(body, include_full_saju=True)
    assert out["schema"] == "manseryeok_engine_lookup_v1"
    assert out["hypothesis_tier"] == "B"
    assert out["track_wall"]["llm_computes_pillars"] is False
    fp = out["four_pillars"]
    assert fp["year"] and fp["month"] and fp["day"] and fp["hour"]
    ei = out["resolution"]["engine_inputs"]
    assert ei["year"] == 1992
    assert ei["month"] == 3
    assert ei["day"] == 13
    assert ei["hour"] == 2


def test_cli_smoke(tmp_path: Path) -> None:
    out = tmp_path / "lookup.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/manseryeok_engine_lookup_v1.py"),
            "--utc-instant",
            "1992-03-12T17:00:00Z",
            "--iana-tz",
            "Asia/Seoul",
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["four_pillars"]["day"]


def test_contract_file_exists():
    p = ROOT / "docs/final/artifacts/MANSE_ENGINE_LOOKUP_API_V1_CONTRACT.json"
    assert p.is_file()
    obj = json.loads(p.read_text(encoding="utf-8"))
    assert obj["runner_cli"] == "scripts/manseryeok_engine_lookup_v1.py"
