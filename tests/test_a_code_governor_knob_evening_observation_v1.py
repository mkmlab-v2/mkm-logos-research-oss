"""RQ-028 P5 evening governor observation tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_a_code_governor_knob_evening_observation_v1.py"
SESSION_PANEL = ROOT / "reports/btrack_session_myeongni_panel_202606_june_prophecy.csv"

FORBIDDEN_KEYS = frozenset(
    {
        "price_directional_hit_rate",
        "jaccard",
        "saving_pct",
        "live_trading",
    }
)


def _assert_no_forbidden_keys(obj: object, path: str = "") -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            assert key not in FORBIDDEN_KEYS, f"forbidden key at {path}.{key}"
            _assert_no_forbidden_keys(value, f"{path}.{key}" if path else key)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _assert_no_forbidden_keys(item, f"{path}[{i}]")


def test_evening_observation_builds_one_line(tmp_path: Path) -> None:
    if not SESSION_PANEL.is_file():
        pytest.skip("june session panel CSV not on disk")
    out = tmp_path / "evening_obs.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--session-date",
            "2026-06-05",
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "a_code_governor_knob_evening_observation_v1"
    assert doc.get("rq_id") == "RQ-028"
    assert doc.get("research_only") is True
    assert doc.get("non_gating") is True
    line = doc.get("evening_append_line") or ""
    assert "[HYPO" in line
    assert "λ=" in line
    assert doc.get("profile_source") in {"example", "local", "env", "explicit"}
    knobs = doc.get("adjusted_knobs") or {}
    assert "token_budget_lambda" in knobs
    _assert_no_forbidden_keys(doc)


def test_evening_observation_cli_prints_line(tmp_path: Path) -> None:
    if not SESSION_PANEL.is_file():
        pytest.skip("june session panel CSV not on disk")
    out = tmp_path / "evening_obs2.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--session-date",
            "2026-06-05",
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "A-code S2" in proc.stdout
