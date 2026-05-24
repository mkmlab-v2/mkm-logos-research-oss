"""Phase A: daily eval must not overwrite commander headline KPI without flag."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.prophecy_hit_rate_ssot_v1 import DAILY_OPERATIONAL, HEADLINE_KPI


def test_eval_refuses_headline_write_without_flag(tmp_path: Path) -> None:
    score = {
        "rows": [
            {"instrument": "btc", "predicted_direction": "bull", "actual_direction": "bull"},
        ]
    }
    score_path = tmp_path / "score.json"
    score_path.write_text(json.dumps(score), encoding="utf-8")
    backup = HEADLINE_KPI.read_text(encoding="utf-8") if HEADLINE_KPI.is_file() else None
    cmd = [
        sys.executable,
        str(_ROOT / "scripts" / "eval_prophecy_hit_rate_v1.py"),
        "--run-mode",
        "price",
        "--score-json",
        str(score_path),
        "--output",
        str(HEADLINE_KPI),
    ]
    try:
        proc = subprocess.run(cmd, cwd=str(_ROOT), capture_output=True, text=True)
        assert proc.returncode == 2
        assert "allow-headline-write" in (proc.stderr or "").lower()
        if backup is not None:
            assert HEADLINE_KPI.read_text(encoding="utf-8") == backup
    finally:
        if backup is not None:
            HEADLINE_KPI.write_text(backup, encoding="utf-8")


def test_eval_default_out_is_daily_operational() -> None:
    from scripts.eval_prophecy_hit_rate_v1 import DEFAULT_OUT

    assert DEFAULT_OUT.resolve() == DAILY_OPERATIONAL.resolve()


def test_is_headline_kpi_path() -> None:
    from scripts.prophecy_hit_rate_ssot_v1 import is_headline_kpi_path

    assert is_headline_kpi_path(HEADLINE_KPI)
    assert not is_headline_kpi_path(DAILY_OPERATIONAL)
