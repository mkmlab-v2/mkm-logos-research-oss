from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_retrieval_eval_runs() -> None:
    cp = subprocess.run(
        [sys.executable, str(_ROOT / "scripts/build_logos_themed_retrieval_eval_v1.py")],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr
    out = _ROOT / "reports/logos_themed_retrieval_eval_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert len(doc.get("themes") or []) == 2


def test_dual_digest_runs() -> None:
    cp = subprocess.run(
        [sys.executable, str(_ROOT / "scripts/build_logos_commander_dual_theme_digest_v1.py")],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert cp.returncode == 0, cp.stderr
    md = _ROOT / "reports/logos_track_b_commander_dual_theme_digest_latest.md"
    assert md.is_file()
    body = md.read_text(encoding="utf-8")
    assert "dan_aramaic" in body and "john_1_logos" in body
