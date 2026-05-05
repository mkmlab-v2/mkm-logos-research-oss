from __future__ import annotations

import json
from pathlib import Path


def test_status_chain_script_exists() -> None:
    path = Path(__file__).resolve().parents[1] / "scripts" / "run_sasang_commercialization_status_chain.py"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "sasang_commercialization_status_chain_v1" in text
    assert "sasang_repro_command_set_latest.txt" in text
    assert "emit_sasang_supplemental_trend_alert.py" in text
