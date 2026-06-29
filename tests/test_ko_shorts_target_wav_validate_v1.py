"""Target WAV validate CLI smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_target_wav_validate_cli() -> None:
    out = ROOT / "reports/ko_shorts_target_wav_validate_test_v1.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_ko_shorts_target_wav_validate_v1.py"),
            "--case-id",
            "web_pansori",
            "--profile",
            "netflix_v16_pro",
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    doc = json.loads(out.read_text(encoding="utf-8")) if out.is_file() else {}
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert doc.get("schema") == "ko_shorts_target_wav_validate_v1"
    assert doc.get("qa_auto_pass") is True
